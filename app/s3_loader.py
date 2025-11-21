import boto3
from io import BytesIO
from PIL import Image
from app.config import Config

s3 = boto3.client("s3", region_name=Config.AWS_REGION)

def load_image_s3(key: str):
    """
    S3에서 이미지 불러오기
    """
    obj = s3.get_object(Bucket=Config.S3_BUCKET, Key=key)
    img_bytes = obj["Body"].read()
    return Image.open(BytesIO(img_bytes))
