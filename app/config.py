import os

class Config:
    AWS_REGION = "ap-northeast-2"
    S3_BUCKET = os.getenv("S3_BUCKET", "marketpro-images")  # 필요 시 수정

    MODEL_PATH = "models/yolov8n.pt"

    # DB 연동 시 여기 추가
    MYSQL_HOST = os.getenv("MYSQL_HOST", "")
    MYSQL_USER = os.getenv("MYSQL_USER", "")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "")
