from fastapi import FastAPI, Form
from app.s3_loader import load_image_s3
from app.yolo_engine import detect_products
from app.ocr_engine import extract_price
from app.sku_engine import match_sku

app = FastAPI(
    title="MarketPro AI Lite",
    description="YOLO(보조) + OCR(가격표) + SKU Matching API (Free-tier CPU Version)",
    version="1.1.0"
)


@app.get("/")
def root():
    return {"status": "ok", "message": "MarketPro AI Lite Server Running"}


@app.post("/analyze")
async def analyze(
    s3_key: str = Form(...),
    corner_type: str = Form("냉장"),      # "냉장" | "냉동" (지금은 참고용, 추후 분기 로직에 활용)
    layout_type: str = Form("A"),         # "A" 평선반형 | "B" 바구니형
):
    """
    이미지 분석 API

    s3_key: S3 파일 경로
    corner_type: 촬영한 코너 종류 (냉장/냉동) — 지금은 응답에 참고 정보로만 포함
    layout_type: 가격표 배치 패턴 ("A": 평선반형 / "B": 바구니형)
                 사용자가 촬영 전 선택(방법1)한 값을 그대로 전달받음
    """
    img = load_image_s3(s3_key)

    yolo = detect_products(img)
    ocr = extract_price(img)
    sku = match_sku(yolo, ocr, layout_type=layout_type)

    return {
        "corner_type": corner_type,
        "layout_type": layout_type,
        "yolo": yolo,
        "ocr": {
            "price_tags": [t["text"] for t in ocr["_blocks"]["price_tags"]],
            "filtered_banner_count": len(ocr["_blocks"]["filtered_banners"]),
        },
        "sku": sku,
    }
