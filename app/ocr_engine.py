import easyocr

# EasyOCR Reader
reader = easyocr.Reader(['en', 'ko'], gpu=False)

def extract_price(pil_img):
    """
    가격 텍스트 추출
    """
    results = reader.readtext(pil_img)
    texts = [res[1] for res in results]
    text_joined = " ".join(texts)

    # 숫자만 추출
    import re
    numbers = re.findall(r"\d{2,5}", text_joined)

    return {
        "raw_text": text_joined,
        "detected_numbers": numbers[:5]
    }
