# ocr_engine.py
# ============================================
# 역할: 이미지에서 텍스트를 좌표(bbox)와 함께 추출하고,
#       가격/날짜/규격(중량) 등 패턴별로 분류한다.
#
# ⚠️ 인터페이스 계약 (모듈 교체 대비, 2026.07.08 확정):
#   - 내부 구현은 EasyOCR (당분간 유지, PaddleOCR/GPT Vision 전환은 2차 최적화 단계)
#   - 공개 함수 extract_price(pil_img)의 반환 스키마는 "계약"으로 취급한다.
#     이 스키마만 유지하면 내부 엔진을 바꿔도 sku_engine.py는 수정 불필요.
#     반환 스키마:
#       {
#         "raw_text": str,
#         "detected_numbers": [str, ...],
#         "_blocks": {
#           "price_tags": [ {"text": str, "bbox": [[x,y],...], "center": (x,y),
#                             "confidence": float}, ... ],
#           "name_candidates": [ 위 + "quality_score": float(0~1) 추가, ... ],
#           "filtered_banners": [ {"text": str, "bbox": [[x,y],...]}, ... ],
#         }
#       }
#     (2026.07.09: confidence/quality_score는 계약 외 추가 필드 — 기존 소비자는
#      이 키를 안 쓰므로 무해하지만, sku_engine.py는 이제부터 quality_score를
#      필수로 사용함. 엔진 교체 시 quality_score도 반드시 함께 채워줄 것.)
#   - 엔진 교체 시 extract_text_blocks() 내부만 다시 구현하고, 위 반환 형식은 그대로 유지할 것.
#
# 이전 버전 대비 변경점:
#   1. 좌표(bbox) 정보를 버리지 않고 함께 반환 (공간 매칭에 필수)
#   2. 가격 정규식을 쉼표 포함 패턴으로 교체 (오탐 감소)
#   3. 텍스트 박스 크기로 대형 프로모션 배너를 걸러냄
# ============================================

import re
import numpy as np
from PIL import ImageOps
import easyocr

reader = easyocr.Reader(['en', 'ko'], gpu=False)

PRICE_PATTERN = re.compile(r"\d{1,3}(,\d{3})+")          # 예: 9,990 / 11,880
DATE_PATTERN = re.compile(r"^\d{8}$")                      # 예: 20260702
SPEC_PATTERN = re.compile(r"\d+\s*(g|kg|ml|G|KG|ML)\b")   # 예: 800g, 1kg

# 2026.07.09 — OCR 후보 품질 필터 (거리 계산 이전 단계)
# NAME_PROXIMITY_PX(sku_engine.py)를 150까지 낮춰본 실험 결과, 거리만 줄여서는
# "잡음이 섞이는 문제"만 줄어들 뿐 "그 자리에 있는 텍스트 자체가 쓰레기이거나
# 아예 없는 문제"는 해결이 안 되는 것으로 확인됨 (라면 매대 실측 테스트, 2026.07.09).
# → 거리 계산 전에 후보 텍스트 자체의 "진짜 상품명일 가능성"을 먼저 점수화해서 거른다.
#
# ⚠️ 아래 BANNER_PHRASES는 이번에 관찰된 잡음 문구를 하드코딩한 임시 블록리스트임.
#    매장이 늘어날수록 계속 문구를 추가해줘야 하는 구조적 한계가 있으므로,
#    장기적으로는 YOLO로 매대(진열 영역) 자체를 먼저 크롭해서 천장 배너/POP을
#    원천적으로 OCR 대상에서 제외하는 방향(우선순위 2번 과제)이 근본 해결책임.
BANNER_PHRASES = {
    "롯데마트", "이마트", "전문", "세프가", "셰프가", "만든", "간편식",
    "브랜드", "브래드", "요리하다", "오리하다", "행사상품", "신상품",
}

# 이 점수(0~1) 미만인 후보는 상품명 후보에서 제외 (sku_engine.py에서 사용)
MIN_CANDIDATE_QUALITY = 0.35

# 대형 프로모션 배너 판별 기준: 텍스트 박스 높이가 이미지 전체 높이의 이 비율보다 크면 배너로 간주
BANNER_HEIGHT_RATIO = 0.12

# 최근 스마트폰 카메라(예: 5712x4284, 24MP급) 원본을 그대로 EasyOCR에 넣으면
# 내부 리사이즈/검출 단계에서 텍스트가 낱글자로 쪼개지는 문제가 확인됨 (2026.07.08).
# → OCR 실행 전 가로/세로 중 큰 쪽을 이 값으로 맞춰 축소한다.
#
# 2026.07.08 (냉동육 → 라면 매대 전환 테스트 중 발견):
#   기존 1600 기준으로는 가격표 인식이 0건으로 나오는 문제 확인.
#   라면 매대는 SKU가 훨씬 촘촘하게 배치되어(진열대 1단에 5~8개),
#   가격표 자체가 원본 대비 차지하는 비율이 냉동육 매대보다 훨씬 작음.
#   5712px 기준 1600으로 축소하면 스케일이 0.28배가 되어, 원본에서
#   40~50px 정도이던 가격표 숫자가 11~14px까지 줄어들어 EasyOCR가
#   아예 텍스트로 검출하지 못하는 것으로 추정됨(분류 실패가 아니라 검출 자체 실패).
#   → 2400으로 상향. 그래도 0건이면 2800~3000까지 올려서 재시도해볼 것.
#   (값을 올릴수록 가격표는 더 잘 잡히지만 처리 속도는 느려짐 — 트레이드오프)
OCR_MAX_DIMENSION = 2400


def _resize_for_ocr(pil_img, max_dim=OCR_MAX_DIMENSION):
    """OCR 인식률을 위해 큰 이미지를 축소. (scale은 축소 비율, 좌표 역변환에 사용)"""
    w, h = pil_img.size
    if max(w, h) <= max_dim:
        return pil_img, 1.0
    scale = max_dim / max(w, h)
    resized = pil_img.resize((int(w * scale), int(h * scale)))
    return resized, scale


def _bbox_height(bbox):
    ys = [p[1] for p in bbox]
    return max(ys) - min(ys)


def _bbox_center(bbox):
    xs = [p[0] for p in bbox]
    ys = [p[1] for p in bbox]
    return (sum(xs) / len(xs), sum(ys) / len(ys))


def _text_composition(text):
    """공백을 제외한 글자 구성 비율(한글/숫자/영문)을 계산."""
    chars = [c for c in text if not c.isspace()]
    total = len(chars) or 1
    hangul = sum(1 for c in chars if '\uac00' <= c <= '\ud7a3')
    digit = sum(1 for c in chars if c.isdigit())
    latin = sum(1 for c in chars if c.isalpha() and c.isascii())
    return {
        "total": total,
        "hangul_ratio": hangul / total,
        "digit_ratio": digit / total,
        "latin_ratio": latin / total,
    }


def score_candidate_quality(text, confidence=1.0):
    """
    OCR 후보 텍스트가 '진짜 상품명일 가능성'을 0~1 점수로 반환.
    거리 계산(sku_engine._gather_nearby_text) 이전에 먼저 적용되는 필터용 점수.

    조합 기준 (요청 반영):
      1. 한글 비율 — 높을수록 가점
      2. 숫자 비율 — 순수 숫자(브랜드 연도/코드 등)는 즉시 0점
      3. 영어 비율 — 높을수록 감점
      4. 배너/POP 문구 블록리스트 — 포함 시 즉시 0점
      5. 최소 글자수 — 2글자 미만은 즉시 0점
      6. OCR confidence — 그대로 가중 반영
    """
    clean = text.strip()
    if not clean:
        return 0.0

    # 4) 배너/POP 문구 블록리스트: 부분 일치만 되어도 배너로 간주하고 탈락
    for phrase in BANNER_PHRASES:
        if phrase in clean:
            return 0.0

    comp = _text_composition(clean)

    # 5) 최소 글자수
    if comp["total"] < 2:
        return 0.0

    # 2) 순수 숫자만인 후보 (콤마가 없어 가격표로도 못 잡히고 남은 것들 —
    #    "1963" 같은 브랜드 연도, 진열대 코드 등일 확률이 높음)
    if comp["digit_ratio"] == 1.0:
        return 0.0

    score = 0.0
    # 1) 한글 비율 가점 (카탈로그 상품명이 전부 한글이므로 가장 큰 가중치)
    score += comp["hangul_ratio"] * 0.5
    # 3) 영어 비율 감점 (한글 매대에서 순수 영문 토큰은 대개 OCR 오독/로고 파편)
    score += (1 - comp["latin_ratio"]) * 0.2
    # 6) OCR 자체 confidence 반영
    score += confidence * 0.3

    return round(min(score, 1.0), 3)


def extract_text_blocks(pil_img):
    """
    이미지에서 텍스트 블록을 추출하고, 각 블록을 유형별로 분류해서 반환.
    (내부 구현: EasyOCR. 엔진 교체 시 이 함수만 다시 구현하면 됨.)

    반환 형식:
    {
        "price_tags": [ {"text": "9,990", "bbox": [...], "center": (x,y)}, ... ],
        "name_candidates": [ {"text": "IFF 닭가슴살", "bbox": [...], "center": (x,y)}, ... ],
        "filtered_banners": [ {"text": "...", "bbox": [...]}, ... ]  # 참고용 (제외된 것들)
    }
    """
    # 스마트폰 사진은 실제 픽셀은 가로로 저장되고 EXIF에 "회전해서 보라"는
    # 방향 정보만 별도로 붙는 경우가 많음. PIL.Image.open()은 이 EXIF를
    # 무시하므로, 그대로 OCR에 넣으면 세로사진이 옆으로 누운 채로 인식되어
    # 텍스트가 낱글자로 조각나는 문제가 발생함 (2026.07.08 확인).
    # → 여기서 EXIF 방향을 실제 픽셀 회전으로 반영(bake-in)한다.
    pil_img = ImageOps.exif_transpose(pil_img)

    img_w, img_h = pil_img.size

    ocr_img, scale = _resize_for_ocr(pil_img)
    img_array = np.array(ocr_img)
    results = reader.readtext(img_array)  # [(bbox, text, confidence), ...] (축소된 이미지 좌표계)

    price_tags = []
    name_candidates = []
    filtered_banners = []

    for bbox, text, conf in results:
        # 좌표를 원본 이미지 픽셀 기준으로 환산 (축소 전 상태와 동일한 좌표계 유지)
        if scale != 1.0:
            bbox = [[x / scale, y / scale] for x, y in bbox]

        height = _bbox_height(bbox)
        center = _bbox_center(bbox)
        clean_text = text.strip()

        # 대형 배너(프로모션 사인)로 추정되는 큰 글자는 제외
        if height / img_h > BANNER_HEIGHT_RATIO:
            filtered_banners.append({"text": clean_text, "bbox": bbox})
            continue

        if PRICE_PATTERN.search(clean_text):
            price_tags.append({"text": clean_text, "bbox": bbox, "center": center, "confidence": round(float(conf), 3)})
        elif DATE_PATTERN.match(clean_text.replace("-", "").replace(".", "")):
            # 날짜류는 상품명 후보에서도 제외 (가격표 안의 판매기간 텍스트 등)
            continue
        else:
            # 규격(중량) 텍스트도 상품명 후보에 포함 — SKU 매칭 시 참고 정보로 활용
            # quality_score: 거리 계산 전에 sku_engine에서 먼저 필터링하는 용도로 미리 계산해둠
            name_candidates.append({
                "text": clean_text,
                "bbox": bbox,
                "center": center,
                "confidence": round(float(conf), 3),
                "quality_score": score_candidate_quality(clean_text, conf),
            })

    return {
        "price_tags": price_tags,
        "name_candidates": name_candidates,
        "filtered_banners": filtered_banners,
        # ⚠️ 계약 외 추가 필드 (디버깅용) — 기존 소비자(sku_engine 등)는 이 키를 안 쓰므로 무해함.
        # "OCR이 이미지에서 텍스트를 몇 개나 찾았는지"를 바로 보여줘서,
        # 0건일 때 "애초에 텍스트 검출 자체가 안 된 것"인지 "분류 규칙에서 걸러진 것"인지 구분하는 용도.
        "debug_total_raw_blocks": len(results),
    }


def extract_price(pil_img):
    """
    공개 인터페이스 — main.py / test_ocr_sku.py / sku_engine.py가 호출하는 진입점.
    (신규 로직은 extract_text_blocks()를 사용, 이 함수는 하위호환 + 계약 유지용)
    """
    blocks = extract_text_blocks(pil_img)
    prices = [b["text"] for b in blocks["price_tags"]]
    return {
        "raw_text": " ".join(prices),
        "detected_numbers": prices[:5],
        "_blocks": blocks,  # sku_engine에서 좌표 정보가 필요하므로 함께 전달
        "debug_total_raw_blocks": blocks.get("debug_total_raw_blocks", 0),  # 계약 외 추가 필드 (디버깅용)
    }
