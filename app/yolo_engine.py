from ultralytics import YOLO
import numpy as np
import cv2
from app.config import Config

# ============================================
# 2026.07.09 — YOLO 탐지 0건 문제 해결 (COCO → Open Images V7 전환)
#
# 그동안 Config.MODEL_PATH(yolov8n.pt, COCO 80종 기본모델)로는 라면/식품
# 패키지 자체가 인식 대상 클래스에 없어서 항상 0건이 나왔음. COCO는 사람/자동차/
# 개 같은 일상 객체 위주라 매대에 진열된 포장 식품과는 애초에 안 맞는 모델이었음.
#
# ultralytics가 공식 제공하는 Open Images V7 사전학습 가중치(yolov8n-oiv7.pt)로
# 교체함 — 600개 클래스를 다루고 그중 "Packaged goods", "Food", "Snack" 등
# 포장 상품과 관련된 카테고리가 있어 매대 제품 박스를 잡아낼 확률이 훨씬 높음.
#
# ⚠️ 이 프로젝트는 YOLO로 "정확히 어떤 상품인지" 분류하지 않고(상품명은 OCR로만
#    판단, sku_engine.py 참고) 페이싱(진열 개수) 카운트용 박스만 필요하므로,
#    OIV7이 세부 상품 종류까진 몰라도 "포장 상품이 여기 있다"만 잡아주면
#    이 프로젝트 목적에는 충분함.
#
# ⚠️ yolov8n-oiv7.pt는 최초 1회 실행 시 ultralytics가 자동으로 다운로드함
#    (인터넷 연결 필요, 약 6MB). Config.MODEL_PATH(로컬 COCO 가중치 경로)는
#    당장은 안 쓰지만 롤백 대비 그대로 남겨둠.
#
# ⚠️ 이것도 최종 해결책은 아님 — 여전히 "포장 상품"이라는 일반 개념으로만
#    잡는 것이라, 라면/만두/밥 같은 세부 카테고리 구분이나 정확한 개별 SKU
#    facing 카운트 정밀도는 결국 하림산업 매대 사진으로 커스텀 학습해야
#    확실해짐. 지금은 "0건 → 몇 건이라도 잡히는지" 확인하는 실험 단계.
MODEL_PATH_OIV7 = "yolov8n-oiv7.pt"

model = YOLO(MODEL_PATH_OIV7)

def detect_products(pil_img):
    """
    YOLO 기반 상품(포장 물체) 탐지 — Open Images V7 가중치 사용.
    label 값은 참고용일 뿐 신뢰하지 않음 (상품명 판단은 OCR 결과만 사용, sku_engine.py 참고).
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
