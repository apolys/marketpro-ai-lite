def match_sku(yolo_results, ocr_results):
    """
    SKU 매칭 로직 (샘플 버전)
    - YOLO 탐지 라벨 기반 단순 매칭
    - OCR 숫자는 향후 가격 판단에 사용
    """

    matches = []

    for det in yolo_results:
        matches.append({
            "yolo_label": det["label"],
            "predicted_sku": f"SKU-{det['label']}",  # 샘플 매칭
            "match_score": 0.75
        })

    return matches
