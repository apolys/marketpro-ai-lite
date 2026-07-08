# sku_engine.py
# ============================================
# 역할: 가격표(price_tags) 주변의 텍스트(name_candidates)를 모아
#       하림 제품 카탈로그와 매칭하고, 근처 YOLO 박스로 페이싱(진열 수)을 추정한다.
#
# 전략 변경 (2026.07.07):
#   기존 계획 - YOLO로 제품 자체를 인식해서 카탈로그와 이미지 매칭 (커스텀 학습 필요, 무거움)
#   변경 후  - 가격표에 상품명이 이미 인쇄되어 있음을 발견 → OCR 텍스트로 먼저 매칭 (Plan A)
#              YOLO는 페이싱(개수) 카운트 및 재고(빈공간) 판단 보조용으로만 사용
#
# ⚠️ 주의: 지금 연결된 YOLO(yolov8n.pt)는 COCO 기본 모델이라
#          "닭가슴살 포장" 같은 하림 특정 상품을 라벨로 인식하지 못한다.
#          페이싱 카운트는 "이 영역에 물체가 몇 개 있는지"를 보는 용도로만 쓰고,
#          라벨(어떤 상품인지)은 신뢰하지 않는다 — 상품명은 OCR 결과로만 판단한다.
# ============================================

from rapidfuzz import process, fuzz
from app.catalog_data import get_catalog_names, get_catalog_by_index

# 가격표 근처로 볼 최대 거리(픽셀). 이미지 해상도에 따라 조정 필요.
# 2026.07.08: 실제 매대 사진(5712x4284 고해상도) 기준 진단 결과,
# 가격표~상품명 사이 실측 거리가 400~1000px 수준으로 확인되어 값 상향 조정.
# (참고: 원래 값 120은 저해상도 사진을 가정한 초기 추정치였음)
#
# 2026.07.09 (라면 매대 실측 디버그 결과 반영, 실험 단계):
#   debug_nearest_tag_distance / debug_nearby_candidate_distances로 실측한 결과,
#   가격표끼리는 800~1900px로 그리 안 촘촘했지만, 가격표 하나 주변 60~400px
#   반경 안에도 후보 텍스트가 8개씩 잡혀서(브랜드 로고, 프로모션 배너 문구,
#   패키지 디자인 텍스트 등) 600px는 물론 훨씬 좁혀도 여러 개가 섞이는 게 확인됨.
#   → 일단 150으로 낮춰서 "거리만 줄였을 때 개선 정도"를 실험 중.
#
#   ⚠️ 이 값은 최종값이 아님. 다음 단계로:
#     1) OCR 후보 필터 추가 (배너/로고/패키지 텍스트를 애초에 name_candidates에서
#        걸러내는 로직 — 거리만으로는 한계가 있다는 게 이번 실험으로 확인됨)
#     2) YOLO 탐지 0건 원인 해결 (커스텀 학습 또는 대체 모델)
#   최종적으로는 매장/매대 레이아웃마다 밀집도가 다르므로, 이 상수 하나에
#   전역적으로 의존하는 구조에서 벗어나 카테고리/레이아웃별 동적 값 또는
#   가격표-텍스트 그룹핑 알고리즘 자체를 개선하는 방향으로 가야 함.
NAME_PROXIMITY_PX = 150

# 페이싱 카운트 시 가격표 위쪽으로 몇 픽셀까지를 "같은 그룹"으로 볼지
FACING_SEARCH_HEIGHT_A = 220   # 평선반형: 바로 위 트레이 정도 범위
FACING_SEARCH_HEIGHT_B = 400   # 바구니형: 바구니 안 전체를 보려면 더 넓게 잡음

# 카탈로그 매칭 최소 신뢰도 (이 이하면 "매칭 실패"로 처리)
MATCH_SCORE_THRESHOLD = 55


def _distance(p1, p2):
    return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5


def _nearest_other_tag_distance(tag, all_tags):
    """이 가격표와 '다른' 가격표들 사이의 최단 거리.
    → 이 값이 실제 매대에서 가격표끼리 얼마나 촘촘한지를 보여주는 지표.
    NAME_PROXIMITY_PX는 이 값보다 충분히 작아야 옆 제품 텍스트가 안 섞임."""
    others = [t for t in all_tags if t is not tag]
    if not others:
        return None
    return min(_distance(tag["center"], o["center"]) for o in others)


def _nearby_candidate_distances(tag_center, name_candidates, limit=8, max_distance=2000):
    """디버그용 — 이 가격표 기준 가까운 상품명 후보들까지의 실제 거리를 가까운 순으로 나열.
    NAME_PROXIMITY_PX 값을 감으로 잡지 않고, 실제 이 숫자들을 보고 정하기 위한 용도."""
    dists = sorted(
        round(_distance(tag_center, c["center"]), 1)
        for c in name_candidates
        if _distance(tag_center, c["center"]) <= max_distance
    )
    return dists[:limit]


def _gather_nearby_text(tag_center, name_candidates, max_distance=NAME_PROXIMITY_PX):
    """가격표 중심점 근처(max_distance 이내)의 텍스트들을 모아 하나의 문자열로 합침"""
    nearby = [c for c in name_candidates if _distance(tag_center, c["center"]) <= max_distance]
    # 위쪽에 있는 텍스트를 먼저 오도록 y좌표 기준 정렬 (보통 상품명이 가격 위에 인쇄됨)
    nearby.sort(key=lambda c: c["center"][1])
    return " ".join(c["text"] for c in nearby), nearby


def _count_facing(tag_center, tag_bbox, yolo_results, layout_type):
    """가격표 위쪽 영역에 있는 YOLO 탐지 박스 수를 세어 페이싱(진열 수) 추정"""
    search_height = FACING_SEARCH_HEIGHT_A if layout_type == "A" else FACING_SEARCH_HEIGHT_B
    tag_x_min = min(p[0] for p in tag_bbox)
    tag_x_max = max(p[0] for p in tag_bbox)
    tag_y = tag_center[1]

    # 가격표 좌우로 약간의 여유폭을 두고, 그 위쪽 search_height 범위 안의 박스만 카운트
    margin = (tag_x_max - tag_x_min) * 1.5

    count = 0
    for det in yolo_results:
        x1, y1, x2, y2 = det["bbox"]
        box_center_x = (x1 + x2) / 2
        box_center_y = (y1 + y2) / 2
        if (tag_x_min - margin) <= box_center_x <= (tag_x_max + margin):
            if (tag_y - search_height) <= box_center_y <= tag_y:
                count += 1
    return count


def match_sku(yolo_results, ocr_results, layout_type="A"):
    """
    SKU 매칭 메인 함수

    Args:
        yolo_results: yolo_engine.detect_products()의 결과 (페이싱 카운트 보조용)
        ocr_results: ocr_engine.extract_price()의 결과 (내부에 _blocks로 좌표 포함)
        layout_type: "A" (평선반형) 또는 "B" (바구니형)

    Returns:
        가격표별 매칭 결과 리스트
    """
    blocks = ocr_results.get("_blocks", {"price_tags": [], "name_candidates": []})
    price_tags = blocks["price_tags"]
    name_candidates = blocks["name_candidates"]

    matches = []

    for tag in price_tags:
        combined_text, nearby_texts = _gather_nearby_text(tag["center"], name_candidates)

        if combined_text.strip():
            catalog_names = get_catalog_names()
            best = process.extractOne(combined_text, catalog_names, scorer=fuzz.WRatio)
        else:
            best = None

        facing_count = _count_facing(tag["center"], tag["bbox"], yolo_results, layout_type)

        # 🔍 디버그 전용 — NAME_PROXIMITY_PX(현재 값) 튜닝을 위한 실측 거리.
        # nearest_tag_distance: 이 가격표와 가장 가까운 '다른' 가격표까지의 거리.
        #   → NAME_PROXIMITY_PX가 이 값의 절반 정도보다 크면 옆 제품까지 끌어올 확률이 높음.
        # nearby_candidate_distances: 실제 상품명 후보들까지의 거리를 가까운 순 8개.
        #   → 그 사진에서 "우리 제품 텍스트"가 대략 몇 px 안쪽에 있는지 감을 잡는 용도.
        debug_nearest_tag_distance = _nearest_other_tag_distance(tag, price_tags)
        debug_nearby_candidate_distances = _nearby_candidate_distances(tag["center"], name_candidates)

        if best and best[1] >= MATCH_SCORE_THRESHOLD:
            catalog_idx = best[2]
            catalog_item = get_catalog_by_index(catalog_idx)
            matches.append({
                "price_text": tag["text"],
                "matched_name_text": combined_text,
                "predicted_sku": catalog_item["sku_name"],
                "brand": catalog_item["brand"],
                "spec": catalog_item["spec"],
                "storage_type": catalog_item["storage_type"],
                "match_score": round(best[1], 1),
                "facing_count": facing_count,
                "layout_type": layout_type,
                "debug_nearest_tag_distance": round(debug_nearest_tag_distance, 1) if debug_nearest_tag_distance else None,
                "debug_nearby_candidate_distances": debug_nearby_candidate_distances,
            })
        else:
            # 매칭 실패 — 카탈로그에 없는 상품이거나 OCR 텍스트가 부족한 경우
            matches.append({
                "price_text": tag["text"],
                "matched_name_text": combined_text,
                "predicted_sku": None,
                "match_score": round(best[1], 1) if best else 0,
                "facing_count": facing_count,
                "layout_type": layout_type,
                "note": "매칭 실패 — 카탈로그에 없거나 OCR 인식률 부족",
                "debug_nearest_tag_distance": round(debug_nearest_tag_distance, 1) if debug_nearest_tag_distance else None,
                "debug_nearby_candidate_distances": debug_nearby_candidate_distances,
            })

    return matches
