from ultralytics import YOLO
import numpy as np
import cv2
from app.config import Config

# CPU로도 가능한 초경량 모델 (YOLOv8n)
model = YOLO(Config.MODEL_PATH)

def detect_products(pil_img):
    """
    YOLO 기반 상품 탐지
    """
    img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

    result = model(img, conf=0.25)[0]

    detections = []
    for box in result.boxes:
        cls = int(box.cls)
        conf = float(box.conf)
        xyxy = box.xyxy.tolist()[0]
        label = result.names[cls]

        detections.append({
            "label": label,
            "confidence": conf,
            "bbox": xyxy
        })

    return detections
