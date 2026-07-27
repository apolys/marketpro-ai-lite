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
import re
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

# ── 2026.07.27 스케일링 시도 2건 모두 롤백 ──────────────────────────
# 1차: 이미지 전체 크기 기준 스케일링 → 2차: 가격표(tag_bbox) 크기 기준
# 스케일링, 둘 다 시도했으나 실제 ocr_engine.py의 tag_bbox가 정확히 어떤
# 영역(가격표 전체 카드인지, 숫자 텍스트만의 좁은 박스인지)을 가리키는지
# 확인 없이 추측으로 기준값을 잡아 오히려 ROI가 0으로 붕괴하는 등 결과가
# 더 나빠짐(2026.07.27). 근본 원인 파악 전까지는 원래 안정적으로 동작하던
# 절대 픽셀 고정값(ROI_ABOVE_PX/ROI_HALF_WIDTH_PX)으로 되돌린다.
#
# 재시도 시 선행 조건: ocr_engine.py에서 실제 tag["bbox"]가 어느 영역을
# 가리키는지(가격표 카드 전체 vs 숫자 텍스트만) 먼저 확인하고, 여러 해상도/
# 촬영거리의 실사 사진으로 tag_bbox 크기 분포를 실측한 뒤 스케일링을
# 재설계할 것. 지금처럼 추측치로 기준값을 잡지 말 것.
# ──────────────────────────────────────────────────────────────

# 카탈로그 매칭 최소 신뢰도 (이 이하면 "매칭 실패"로 처리)
MATCH_SCORE_THRESHOLD = 55

# 이 글자수 미만인 조합 텍스트는 카탈로그 매칭 시도 자체를 안 함
# (너무 짧으면 rapidfuzz가 우연히 임계값 이상 점수를 주는 오탐이 확인됨, 2026.07.09)
MIN_MATCH_TEXT_LENGTH = 3

# 품질 필터를 통과한 후보 중에서도, 가까운 순으로 최대 이 개수까지만 합쳐서 매칭에 사용
# (필터를 통과해도 여러 개가 남을 수 있으므로 최종 안전장치로 둠)
MAX_CANDIDATES_PER_TAG = 3


def _distance(p1, p2):
    return ((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2) ** 0.5


# ── 2026.07.27 추가 ──────────────────────────────────────────────
# 한 물리적 ESL(전자가격표)에 "1개 구매 시 가격"과 "N개 이상 구매 시 가격"이
# 함께 인쇄되어 있는 경우(예: 삼양1963 6,150원/5,535원)를 OCR이 별도 텍스트
# 블록 2개로 인식하는 케이스가 확인됨. 매칭 결과만으로는 어느 게 단품가인지
# 멀티바이가인지 구분이 안 되므로, 인식된 가격 숫자를 카탈로그의
# price(단품가)/multi_buy_price(N개이상가)와 비교해 태깅한다.
def _parse_price(text):
    """가격표 텍스트에서 숫자만 뽑아 정수로 변환. 숫자가 없으면 None."""
    digits = re.sub(r"[^0-9]", "", text or "")
    return int(digits) if digits else None


def _price_tier(observed_price, catalog_item):
    """observed_price가 catalog_item의 단품가/멀티바이가 중 어디에 해당하는지 판정.

    두 값 다 있고 정확히 일치하면 확정 라벨을 반환하고, 정확히 일치하지
    않으면(OCR 숫자 오독 등) 더 가까운 쪽에 '(추정)' 표시를 붙여 반환한다.
    카탈로그에 가격 정보 자체가 없는 구 스키마 항목은 None을 반환한다.
    """
    if observed_price is None:
        return None

    single = catalog_item.get("price")
    multi = catalog_item.get("multi_buy_price")
    multi_qty = catalog_item.get("multi_buy_qty") or 2

    if single is None and multi is None:
        return None

    if single is not None and observed_price == single:
        return "단품가"
    if multi is not None and observed_price == multi:
        return f"{multi_qty}개이상가"

    candidates = []
    if single is not None:
        candidates.append(("단품가", abs(observed_price - single)))
    if multi is not None:
        candidates.append((f"{multi_qty}개이상가", abs(observed_price - multi)))
    candidates.sort(key=lambda x: x[1])
    return f"{candidates[0][0]}(추정)"
# ──────────────────────────────────────────────────────────────


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


def _match_catalog(combined_text, catalog_names):
    """
    카탈로그 매칭 — 여러 스코어러 중 최고점을 채택.

    2026.07.09 (클로즈업 사진 테스트에서 발견): ROI+품질필터를 거쳐도, OCR이
    정답 상품명을 정확히 읽었는데도 그 앞뒤에 다른 잡음 글자가 붙어있으면
    (예: "'맨출m 추천 하림더미식 장인라면 업바라맛" 안에 "하림더미식 장인라면"이
    정확히 들어있음) fuzz.WRatio 점수가 낮게 나오는 경우가 확인됨. WRatio는
    전체 문자열 길이 대비 유사도라서, 짧은 정답이 긴 잡음 속에 파묻히면
    불리해지는 구조적 특성 때문.
    → partial_ratio(부분 문자열 정렬)와 token_set_ratio(토큰 집합 교집합)를
      함께 계산해서, 잡음에 파묻힌 정답도 놓치지 않도록 셋 중 최고점을 채택.
    """
    best_overall = None
    for scorer in (fuzz.WRatio, fuzz.partial_ratio, fuzz.token_set_ratio):
        result = process.extractOne(combined_text, catalog_names, scorer=scorer)
        if result and (best_overall is None or result[1] > best_overall[1]):
            best_overall = result
    return best_overall


def _in_price_tag_roi(tag_bbox, candidate_center, roi_above_px=ROI_ABOVE_PX, roi_half_width_px=ROI_HALF_WIDTH_PX):
    """
    가격표 Bounding Box 기준 '위쪽 직사각형 ROI' 안에 후보 중심점이 있는지 판정.
    가격표 아래/좌우 바깥 텍스트는 이 함수 단계에서 원천적으로 제외된다.

    2026.07.27: roi_above_px/roi_half_width_px를 인자로 받도록 변경 —
    이미지 해상도에 비례해 스케일링된 값을 넘길 수 있게 하기 위함
    (호출부에서 값을 안 넘기면 기존 절대 픽셀값 그대로 동작, 하위호환).

    ROI 정의:
      - 세로: 가격표 위쪽 경계(tag_y_min)로부터 roi_above_px만큼 위 ~ 가격표 위쪽 경계까지
        (가격표 자체 높이 영역 및 그 아래는 제외)
      - 가로: 가격표 좌우 경계에서 각각 roi_half_width_px만큼 확장
    """
    tag_x_min = min(p[0] for p in tag_bbox)
    tag_x_max = max(p[0] for p in tag_bbox)
    tag_y_min = min(p[1] for p in tag_bbox)  # 가격표 박스의 "위쪽" 경계 (이미지 좌표계는 아래로 갈수록 y 증가)

    cx, cy = candidate_center

    roi_x_min = tag_x_min - roi_half_width_px
    roi_x_max = tag_x_max + roi_half_width_px
    roi_y_min = tag_y_min - roi_above_px
    roi_y_max = tag_y_min

    return (roi_x_min <= cx <= roi_x_max) and (roi_y_min <= cy <= roi_y_max)


def _gather_nearby_text(tag_bbox, tag_center, name_candidates,
                         roi_above_px=ROI_ABOVE_PX, roi_half_width_px=ROI_HALF_WIDTH_PX):
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
    in_roi = [c for c in name_candidates if _in_price_tag_roi(tag_bbox, c["center"], roi_above_px, roi_half_width_px)]

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


# ── 2026.07.27 추가 ──────────────────────────────────────────────
# 데모 페이지에서 "인식된 주변 텍스트"를 사람이 수동으로 고쳐서 즉시
# 재매칭해볼 수 있게 하기 위한 공개 함수. OCR/ROI/이미지 재분석 없이,
# 텍스트 하나만 받아서 카탈로그와 바로 매칭한다. 사진을 다시 찍거나
# 파이프라인을 다시 돌리지 않고도 "이 텍스트였다면 매칭이 맞는지"를
# 즉시 검증할 수 있다 (예: OCR이 깨뜨린 텍스트를 정답으로 고쳐서 확인).
def match_catalog_text(combined_text):
    """편집된 텍스트를 카탈로그와 직접 매칭. OCR/ROI 파이프라인과 무관하게
    동작하며, match_sku()가 매칭 성공 시 반환하는 것과 동일한 필드 구성으로
    결과를 반환한다."""
    combined_text = (combined_text or "").strip()
    if len(combined_text) < MIN_MATCH_TEXT_LENGTH:
        return {
            "matched_name_text": combined_text,
            "predicted_sku": None,
            "match_score": 0,
            "note": "텍스트가 너무 짧습니다 (최소 길이 미달)",
        }

    catalog_names = get_catalog_names()
    best = _match_catalog(combined_text, catalog_names)

    if not best or best[1] < MATCH_SCORE_THRESHOLD:
        return {
            "matched_name_text": combined_text,
            "predicted_sku": None,
            "match_score": round(best[1], 1) if best else 0,
            "note": "매칭 실패 — 카탈로그에 없거나 텍스트 유사도 부족",
        }

    catalog_item = get_catalog_by_index(best[2])
    return {
        "matched_name_text": combined_text,
        "predicted_sku": catalog_item.get("sku") or catalog_item.get("sku_name"),
        "brand": catalog_item.get("brand"),
        "company": catalog_item.get("company"),
        "product_group": catalog_item.get("product_group"),
        "spec": catalog_item.get("spec") or catalog_item.get("ea"),
        "storage_type": catalog_item.get("storage_type"),
        "price": catalog_item.get("price"),
        "multi_buy_price": catalog_item.get("multi_buy_price"),
        "multi_buy_qty": catalog_item.get("multi_buy_qty"),
        "discount_rate": catalog_item.get("discount_rate"),
        "barcode": catalog_item.get("barcode"),
        "match_score": round(best[1], 1),
    }
# ──────────────────────────────────────────────────────────────


def match_sku(yolo_results, ocr_results, layout_type="A", image_size=None):
    """
    SKU 매칭 메인 함수

    Args:
        yolo_results: yolo_engine.detect_products()의 결과 (페이싱 카운트 보조용)
        ocr_results: ocr_engine.extract_price()의 결과 (내부에 _blocks로 좌표 포함)
        layout_type: "A" (평선반형) 또는 "B" (바구니형)
        image_size: (width, height) — 진단 로그 출력용으로만 사용(참고용).
            2026.07.27 해상도/촬영거리 대응 스케일링을 두 차례 시도했으나
            (이미지 전체 크기 기준 → 가격표 크기 기준) 둘 다 tag_bbox의
            실제 의미를 확인 안 한 추측이라 결과가 악화되어 전부 롤백함.
            ROI는 다시 절대 픽셀 고정값(ROI_ABOVE_PX/ROI_HALF_WIDTH_PX)을 사용.

    Returns:
        가격표별 매칭 결과 리스트
    """
    blocks = ocr_results.get("_blocks", {"price_tags": [], "name_candidates": []})
    price_tags = blocks["price_tags"]
    name_candidates = blocks["name_candidates"]

    # 🔍 진단용 (2026.07.27) — "사진에 보이는 가격표 개수"와 "OCR이 실제로 검출한
    # 가격표 개수"가 일치하는지 확인하기 위한 로그. 다른 개수라면 이후 매칭
    # 이전 단계(OCR 가격표 검출 자체)에서 누락/가림이 있었다는 뜻이므로,
    # 원인이 사진 촬영(가림)인지 코드(검출 로직)인지 구분하는 첫 단서가 된다.
    # 확인이 끝나면 이 줄은 지워도 무방.
    print(f"[진단] OCR이 검출한 가격표(price_tags) 개수: {len(price_tags)}")
    print(f"[진단] image_size={image_size} (참고용)")
    # 🔍 진단용 (2026.07.27) — 향후 해상도별 스케일링을 다시 시도하려면, 그 전에
    # 반드시 이 로그로 실제 tag_bbox 크기 분포부터 실측해야 한다(추측 금지).
    for _t in price_tags:
        _xs = [p[0] for p in _t["bbox"]]
        _ys = [p[1] for p in _t["bbox"]]
        print(f"[진단] price_tag bbox 크기: 폭={max(_xs)-min(_xs):.1f}px, 높이={max(_ys)-min(_ys):.1f}px")

    matches = []

    for tag in price_tags:
        combined_text, nearby_texts = _gather_nearby_text(tag["bbox"], tag["center"], name_candidates)

        # 🔍 디버그 전용 — ROI 방식이 실제로 후보를 얼마나 좁히는지 확인용
        debug_roi_raw_count = sum(1 for c in name_candidates if _in_price_tag_roi(tag["bbox"], c["center"]))
        debug_roi_after_quality_count = len(nearby_texts)

        # 2026.07.09: 너무 짧은 텍스트(예: "'이")는 rapidfuzz가 우연히 높은
        # 점수(임계값 이상)를 줄 수 있음이 확인됨 — 애초에 매칭 시도 자체를 안 함.
        if combined_text.strip() and len(combined_text.strip()) >= MIN_MATCH_TEXT_LENGTH:
            catalog_names = get_catalog_names()
            best = _match_catalog(combined_text, catalog_names)
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
            observed_price = _parse_price(tag["text"])
            matches.append({
                "price_text": tag["text"],
                "matched_name_text": combined_text,
                # 기존 필드 — demo_app.py 렌더링과의 호환을 위해 키 이름/의미 유지
                "predicted_sku": catalog_item.get("sku") or catalog_item.get("sku_name"),
                "brand": catalog_item.get("brand"),
                "spec": catalog_item.get("spec") or catalog_item.get("ea"),
                "storage_type": catalog_item.get("storage_type"),
                # 신규 필드 — 2026.07.27 카탈로그 스키마 확장분 (company/가격/멀티바이/바코드)
                # 구 스키마 항목(신선육/냉동 등)은 해당 키가 없으므로 None으로 채워짐
                "company": catalog_item.get("company"),
                "product_group": catalog_item.get("product_group"),
                "price": catalog_item.get("price"),
                "multi_buy_price": catalog_item.get("multi_buy_price"),
                "multi_buy_qty": catalog_item.get("multi_buy_qty"),
                "discount_rate": catalog_item.get("discount_rate"),
                "barcode": catalog_item.get("barcode"),
                # 2026.07.27 추가 — 이 가격표가 단품가인지 N개이상가인지 구분
                "observed_price": observed_price,
                "price_tier": _price_tier(observed_price, catalog_item),
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
