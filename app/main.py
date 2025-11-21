from fastapi import FastAPI, Form
from app.s3_loader import load_image_s3
from app.yolo_engine import detect_products
from app.ocr_engine import extract_price
from app.sku_engine import match_sku

app = FastAPI(
    title="MarketPro AI Lite",
    description="YOLO + OCR + SKU Matching API (Free-tier CPU Version)",
    version="1.0.0"
)

@app.get("/")
def root():
    return {"status": "ok", "message": "MarketPro AI Lite Server Running"}

@app.post("/analyze")
async def analyze(s3_key: str = Form(...)):
    """
    이미지 분석 API
    s3_key: S3 파일 경로
    """
    img = load_image_s3(s3_key)

    yolo = detect_products(img)
    ocr = extract_price(img)
    sku = match_sku(yolo, ocr)

    return {
        "yolo": yolo,
        "ocr": ocr,
        "sku": sku
    }
