#!/usr/bin/env python3
# ============================================
# test_ocr_sku.py
# 서버(uvicorn) 없이 바로 실행해서 결과를 확인하는 간단 테스트 스크립트.
#
# 사용법:
#   python3 test_ocr_sku.py 이미지경로_또는_URL [corner_type] [layout_type]
#
# 예)
#   python3 test_ocr_sku.py test1.jpg 냉장 A
#   python3 test_ocr_sku.py https://example.com/shelf.jpg 냉동 B
#
# 로컬 파일 경로, http(s) URL 둘 다 지원.
# S3 key를 쓰고 싶으면 S3_KEY=파일명 형태로 전달 (예: S3_KEY=test1.jpg)
# ============================================

import sys
import json
import requests
from io import BytesIO
from PIL import Image

sys.path.insert(0, ".")  # marketpro-ai-lite 루트에서 실행한다고 가정

from app.ocr_engine import extract_price
from app.yolo_engine import detect_products
from app.sku_engine import match_sku


def load_image(source):
    if source.startswith("S3_KEY="):
        from app.s3_loader import load_image_s3
        key = source.replace("S3_KEY=", "")
        print(f"[불러오는 중] S3에서: {key}")
        return load_image_s3(key)
    elif source.startswith("http://") or source.startswith("https://"):
        print(f"[불러오는 중] URL에서: {source}")
        resp = requests.get(source, timeout=10)
        return Image.open(BytesIO(resp.content)).convert("RGB")
    else:
        print(f"[불러오는 중] 로컬 파일: {source}")
        return Image.open(source).convert("RGB")


def main():
    if len(sys.argv) < 2:
        print("사용법: python3 test_ocr_sku.py 이미지경로_또는_URL [corner_type] [layout_type]")
        sys.exit(1)

    image_source = sys.argv[1]
    corner_type = sys.argv[2] if len(sys.argv) > 2 else "냉장"
    layout_type = sys.argv[3] if len(sys.argv) > 3 else "A"

    img = load_image(image_source)

    print("\n[1/3] YOLO 탐지 실행 중...")
    yolo_results = detect_products(img)
    print(f"  → {len(yolo_results)}개 객체 탐지됨 (COCO 기본 라벨 기준, 참고용)")

    print("\n[2/3] OCR 텍스트 추출 중...")
    ocr_results = extract_price(img)
    price_tags = ocr_results["_blocks"]["price_tags"]
    banners = ocr_results["_blocks"]["filtered_banners"]
    print(f"  → 가격표로 인식된 텍스트: {len(price_tags)}개")
    print(f"  → 대형 배너로 걸러진 텍스트: {len(banners)}개")

    print("\n[3/3] SKU 매칭 실행 중...")
    sku_results = match_sku(yolo_results, ocr_results, layout_type=layout_type)

    print("\n" + "=" * 50)
    print(f"결과 (corner_type={corner_type}, layout_type={layout_type})")
    print("=" * 50)
    print(json.dumps(sku_results, ensure_ascii=False, indent=2))
    print("=" * 50)

    matched = sum(1 for r in sku_results if r.get("predicted_sku"))
    print(f"\n요약: 가격표 {len(price_tags)}개 중 {matched}개 매칭 성공")


if __name__ == "__main__":
    main()
