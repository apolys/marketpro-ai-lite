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
#           "price_tags": [ {"text": str, "bbox": [[x,y],...], "center": (x,y)}, ... ],
#           "name_candidates": [ 위와 동일 형식, ... ],
#           "filtered_banners": [ {"text": str, "bbox": [[x,y],...]}, ... ],
#         }
#       }
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
            price_tags.append({"text": clean_text, "bbox": bbox, "center": center})
        elif DATE_PATTERN.match(clean_text.replace("-", "").replace(".", "")):
            # 날짜류는 상품명 후보에서도 제외 (가격표 안의 판매기간 텍스트 등)
            continue
        else:
            # 규격(중량) 텍스트도 상품명 후보에 포함 — SKU 매칭 시 참고 정보로 활용
            name_candidates.append({"text": clean_text, "bbox": bbox, "center": center})

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
