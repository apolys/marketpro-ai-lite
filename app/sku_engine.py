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
from app.ocr_engine import MIN_CANDIDATE_QUALITY

# 2026.07.09 — ROI(관심영역) 기반 후보 추출로 구조 변경
#
# 그동안 가격표를 중심으로 원형 반경(NAME_PROXIMITY_PX)을 그려서 그 안의 모든
# 텍스트를 모으는 방식이었는데, 이 방식은 "방향" 구분이 없어서 가격표 좌우/아래에
# 있는 옆 제품 텍스트까지 계속 끌어오는 근본적인 한계가 있었음. 600(2026.07.08)
# → 150(2026.07.09)까지 낮춰본 실험 결과, 거리를 줄이면 잡음은 줄지만 진짜
# 상품명 후보까지 같이 사라지는 경우가 확인되어 원형 반경 튜닝은 종료함.
#
# → 상품명은 거의 항상 가격표 "위"에 인쇄되므로, 원이 아니라 가격표 위쪽으로만
#   뻗은 직사각형 ROI를 먼저 잘라내고, 그 안에서만 후보를 본다.
#   가격표 아래/옆은 처음부터 후보 대상에서 제외된다.
#
# ⚠️ 아래 두 값은 실측(400~1000px 범위)을 참고한 초기값이며 최종값이 아님.
#    매장/매대 레이아웃마다 인쇄 위치가 다를 수 있으므로, 추후 실제 여러 매장
#    데이터가 쌓이면 레이아웃별 동적 값으로 분리하는 것이 목표.
ROI_ABOVE_PX = 300       # 가격표 위쪽 경계로부터 이 값(px)까지 위로 ROI 확장 (250~350 범위 중 중간값)
ROI_HALF_WIDTH_PX = 150  # 가격표 좌우로 각각 이 값(px)까지 ROI 확장

# 하위호환/디버그 비교용으로만 유지 — 실제 후보 수집(원형 반경 방식)에는 더 이상 사용하지 않음.
# (ROI 방식으로 완전히 대체됨. _nearby_candidate_distances 등 디버그 함수에서만 참고용으로 사용)
NAME_PROXIMITY_PX = 150

# 페이싱 카운트 시 가격표 위쪽으로 몇 픽셀까지를 "같은 그룹"으로 볼지
# ⚠️ 2026.07.09: YOLO 실험 종료 (COCO 0건, OIV7도 낱개 제품이 아닌 씬 전체를
#    "Convenience store"로 뭉뚱그려 인식 — 매대 상품 단위 검출에는 범용 YOLO가
#    부적합하다는 결론). 페이싱 카운트는 커스텀 학습 전까지 보류하고, 지금은
#    OCR+가격표 기반 SKU 명 매칭 엔진 완성에 집중. 아래 상수/코드는 남겨두되
#    당분간 facing_count는 0으로 나오는 게 정상임.
FACING_SEARCH_HEIGHT_A = 220   # 평선반형: 바로 위 트레이 정도 범위
FACING_SEARCH_HEIGHT_B = 400   # 바구니형: 바구니 안 전체를 보려면 더 넓게 잡음

# 카탈로그 매칭 최소 신뢰도 (이 이하면 "매칭 실패"로 처리)
MATCH_SCORE_THRESHOLD = 55

# 품질 필터를 통과한 후보 중에서도, 가까운 순으로 최대 이 개수까지만 합쳐서 매칭에 사용
# (필터를 통과해도 여러 개가 남을 수 있으므로 최종 안전장치로 둠)
MAX_CANDIDATES_PER_TAG = 3


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


def _in_price_tag_roi(tag_bbox, candidate_center):
    """
    가격표 Bounding Box 기준 '위쪽 직사각형 ROI' 안에 후보 중심점이 있는지 판정.
    가격표 아래/좌우 바깥 텍스트는 이 함수 단계에서 원천적으로 제외된다.

    ROI 정의:
      - 세로: 가격표 위쪽 경계(tag_y_min)로부터 ROI_ABOVE_PX만큼 위 ~ 가격표 위쪽 경계까지
        (가격표 자체 높이 영역 및 그 아래는 제외)
      - 가로: 가격표 좌우 경계에서 각각 ROI_HALF_WIDTH_PX만큼 확장
    """
    tag_x_min = min(p[0] for p in tag_bbox)
    tag_x_max = max(p[0] for p in tag_bbox)
    tag_y_min = min(p[1] for p in tag_bbox)  # 가격표 박스의 "위쪽" 경계 (이미지 좌표계는 아래로 갈수록 y 증가)

    cx, cy = candidate_center

    roi_x_min = tag_x_min - ROI_HALF_WIDTH_PX
    roi_x_max = tag_x_max + ROI_HALF_WIDTH_PX
    roi_y_min = tag_y_min - ROI_ABOVE_PX
    roi_y_max = tag_y_min

    return (roi_x_min <= cx <= roi_x_max) and (roi_y_min <= cy <= roi_y_max)


def _gather_nearby_text(tag_bbox, tag_center, name_candidates, max_distance=NAME_PROXIMITY_PX):
    """
    가격표 기준 ROI(위쪽 직사각형 영역) 안의 텍스트만 모아 하나의 문자열로 합침.

    구조 (2026.07.09 변경 — 원형 반경 방식 폐기):
      가격표 ROI 추출 → 품질 필터(quality_score) → ROI 내부 거리순 정렬 → 조합

    이전에는 가격표를 중심으로 원형 반경(NAME_PROXIMITY_PX) 안의 모든 텍스트를
    모았는데, "방향" 구분이 없어 가격표 아래/옆 텍스트까지 계속 섞여 들어왔음.
    상품명은 거의 항상 가격표 "위"에 인쇄되므로, 먼저 위쪽 ROI로 후보 자체를
    좁혀서(옆/아래 텍스트는 원천 배제) 잡음을 구조적으로 줄인다.
    """
    # 1) ROI 추출 — 가격표 위쪽 직사각형 영역 안에 있는 후보만 남긴다.
    #    (아래/좌우 바깥 텍스트는 이 단계에서 이미 제외됨)
    in_roi = [c for c in name_candidates if _in_price_tag_roi(tag_bbox, c["center"])]

    # 2) 품질 필터 — ROI 안에서도 배너/로고/OCR 오독 후보는 제외
    quality_filtered = [
        c for c in in_roi
        if c.get("quality_score", 1.0) >= MIN_CANDIDATE_QUALITY
    ]

    # 3) ROI 내부에서만 거리 계산 — 가까운 순으로 최대 MAX_CANDIDATES_PER_TAG개만 채택
    quality_filtered.sort(key=lambda c: _distance(tag_center, c["center"]))
    selected = quality_filtered[:MAX_CANDIDATES_PER_TAG]

    # 4) 최종 조합은 읽는 순서(위→아래)로 다시 정렬해서 합침 (상품명이 보통 가격 위에 인쇄됨)
    selected.sort(key=lambda c: c["center"][1])
    return " ".join(c["text"] for c in selected), selected


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
        combined_text, nearby_texts = _gather_nearby_text(tag["bbox"], tag["center"], name_candidates)

        # 🔍 디버그 전용 — ROI 방식이 실제로 후보를 얼마나 좁히는지 확인용
        debug_roi_raw_count = sum(1 for c in name_candidates if _in_price_tag_roi(tag["bbox"], c["center"]))
        debug_roi_after_quality_count = len(nearby_texts)

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
                "debug_roi_raw_count": debug_roi_raw_count,
                "debug_roi_after_quality_count": debug_roi_after_quality_count,
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
                "debug_roi_raw_count": debug_roi_raw_count,
                "debug_roi_after_quality_count": debug_roi_after_quality_count,
            })

    return matches
