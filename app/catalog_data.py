# catalog_data.py
# ============================================
# 임시 하림 제품 카탈로그 (temporary catalog)
# 실제 서비스에서는 DB(MySQL RDS) 테이블로 교체 예정.
# 지금은 사용자가 제공한 샘플 + 실제 매대 사진에서 확인된 항목(하림 IFF 라인)을 합쳐서 구성.
# ============================================

CATALOG = [
    # ── 신선육 (냉장) ──
    {"category": "신선육", "brand": "하림", "product_group": "통닭",
     "sku_name": "AIRLINE 한마리닭", "spec": "600g", "storage_type": "냉장"},
    {"category": "신선육", "brand": "하림", "product_group": "절단육",
     "sku_name": "AIRLINE 조각닭", "spec": "825g", "storage_type": "냉장"},
    {"category": "신선육", "brand": "하림", "product_group": "닭다리",
     "sku_name": "AIRLINE 닭다리", "spec": "460g", "storage_type": "냉장"},
    {"category": "신선육", "brand": "하림", "product_group": "윙/봉",
     "sku_name": "AIRLINE 닭날개봉", "spec": "500g", "storage_type": "냉장"},
    {"category": "신선육", "brand": "자연실록", "product_group": "동물복지",
     "sku_name": "자연실록 동물복지 통닭", "spec": "1050g", "storage_type": "냉장"},
    {"category": "신선육", "brand": "자연실록", "product_group": "동물복지",
     "sku_name": "자연실록 동물복지 닭안심", "spec": "300g", "storage_type": "냉장"},

    # ── 별미요리 (냉장) ──
    {"category": "별미요리", "brand": "하림", "product_group": "닭발",
     "sku_name": "한판 불닭발볶음(매콤한맛)", "spec": "300g", "storage_type": "냉장"},
    {"category": "별미요리", "brand": "하림", "product_group": "닭주물럭",
     "sku_name": "한판 닭주물럭(고추장맛)", "spec": "300g", "storage_type": "냉장"},
    {"category": "별미요리", "brand": "하림", "product_group": "닭근위",
     "sku_name": "한판 닭똥집볶음(소금구이)", "spec": "300g", "storage_type": "냉장"},

    # ── 신선육/무항생제 (냉장, 실제 매대 사진1에서 확인) ──
    {"category": "신선육", "brand": "하림/체리부로", "product_group": "백숙",
     "sku_name": "무항생제백숙", "spec": "800g", "storage_type": "냉장"},

    # ── IFF 부위육 라인 (냉동, 실제 매대 사진2에서 확인) ──
    {"category": "신선육", "brand": "하림", "product_group": "IFF부위육",
     "sku_name": "IFF 가슴살", "spec": "900g", "storage_type": "냉동"},
    {"category": "신선육", "brand": "하림", "product_group": "IFF부위육",
     "sku_name": "IFF 닭안심", "spec": "500g", "storage_type": "냉동"},
    {"category": "신선육", "brand": "하림", "product_group": "IFF부위육",
     "sku_name": "IFF 닭다리", "spec": "600g", "storage_type": "냉동"},
    {"category": "신선육", "brand": "하림", "product_group": "IFF부위육",
     "sku_name": "IFF 닭목살", "spec": "500g", "storage_type": "냉동"},
    {"category": "신선육", "brand": "하림", "product_group": "IFF부위육",
     "sku_name": "IFF 윗날개", "spec": "600g", "storage_type": "냉동"},
    {"category": "신선육", "brand": "하림", "product_group": "IFF부위육",
     "sku_name": "IFF 아랫날개", "spec": "600g", "storage_type": "냉동"},

    # ── 냉동 (용가리) ──
    {"category": "냉동조리식품", "brand": "용가리", "product_group": "치킨",
     "sku_name": "용가리치킨", "spec": "300g", "storage_type": "냉동"},
    {"category": "냉동조리식품", "brand": "용가리", "product_group": "치킨",
     "sku_name": "용가리치킨", "spec": "1kg", "storage_type": "냉동"},
    {"category": "냉동조리식품", "brand": "용가리", "product_group": "치킨볼",
     "sku_name": "용가리 치킨볼 달콤양념", "spec": "450g", "storage_type": "냉동"},
    {"category": "냉동조리식품", "brand": "용가리", "product_group": "치킨볼",
     "sku_name": "용가리 치킨볼 소이갈릭", "spec": "450g", "storage_type": "냉동"},
    {"category": "냉동조리식품", "brand": "용가리", "product_group": "떡갈비",
     "sku_name": "용가리 떡갈비", "spec": "450g", "storage_type": "냉동"},
    {"category": "냉동조리식품", "brand": "용가리", "product_group": "용가리땡",
     "sku_name": "용가리땡", "spec": "500g", "storage_type": "냉동"},

    # ── 냉동 (하림) ──
    {"category": "냉동조리식품", "brand": "하림", "product_group": "치킨너겟",
     "sku_name": "치킨너겟2", "spec": "1kg", "storage_type": "냉동"},
    {"category": "냉동조리식품", "brand": "하림", "product_group": "팝콘치킨",
     "sku_name": "굿초이스 팝콘치킨", "spec": "1kg", "storage_type": "냉동"},
    {"category": "냉동조리식품", "brand": "하림", "product_group": "안심꿔바로우",
     "sku_name": "안심꿔바로우", "spec": "450g", "storage_type": "냉동"},
    {"category": "냉동조리식품", "brand": "하림", "product_group": "순살치킨",
     "sku_name": "소이갈릭 순살치킨", "spec": "350g", "storage_type": "냉동"},

    # ── 라면 (상온, 하림산업 더미식 — 실제 매대 사진 기준 핵심 SKU) ──
    {"category": "라면", "brand": "하림산업", "product_group": "더미식 장인라면",
     "sku_name": "더미식 장인라면 얼큰한맛", "spec": "5입", "storage_type": "상온"},
    {"category": "라면", "brand": "하림산업", "product_group": "더미식 장인라면",
     "sku_name": "더미식 장인라면 담백한맛", "spec": "5입", "storage_type": "상온"},

    # ── 라면 (상온, 경쟁사 벤치마킹용 — 매대 동일 구역에 진열된 제품)
    # ⚠️ 사진 속 라벨이 OCR로 흐릿하게만 확인되어 정확한 스펙은 검증 필요
    {"category": "라면", "brand": "농심", "product_group": "신라면",
     "sku_name": "신라면", "spec": "5입", "storage_type": "상온"},
    {"category": "라면", "brand": "오뚜기", "product_group": "진라면",
     "sku_name": "진라면 매운맛", "spec": "5입", "storage_type": "상온"},
    {"category": "라면", "brand": "삼양식품", "product_group": "삼양라면",
     "sku_name": "삼양라면", "spec": "5입", "storage_type": "상온"},
    {"category": "라면", "brand": "팔도", "product_group": "팔도라면",
     "sku_name": "서울라면", "spec": "5입", "storage_type": "상온"},
]


def get_catalog_names():
    """rapidfuzz 매칭용 — '브랜드 제품명' 형태의 검색 대상 문자열 리스트 반환"""
    return [f"{item['brand']} {item['sku_name']}" for item in CATALOG]


def get_catalog_by_index(idx):
    return CATALOG[idx]
