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

    # ── 라면 (상온) — 롯데마트 실사 사진 + 가격표(ESL) 대조로 확정된 6개 SKU (2026-07-27 검증) ──
    # 구조: company(제조법인)/brand(서브브랜드)/product_group(제품군)은 분리 관리.
    # target_segment(타겟층: 성인/어린이)는 2026.07.27 추가 — 같은 company 안에서도
    # 브랜드별 타겟이 완전히 다른 경우(예: 하림산업의 더미식=성인, 푸디버디=어린이)를
    # 한눈에 구분하기 위함.
    # sku는 아직 육안 검증이 완전히 끝나지 않아, 가격표에 인쇄된 전체 텍스트를 그대로 유지.
    # (추후 검증 완료 시 company/brand 접두어를 제거한 순수 sku로 정제 예정)
    {"category": "라면", "company": "삼양식품", "brand": "삼양1963", "product_group": "삼양1963",
     "target_segment": "성인",
     "sku": "삼양식품 삼양1963", "sku_name": "삼양식품 삼양1963", "spec": "4입", "ea": "4입",
     "storage_type": "상온",
     "price": 6150, "multi_buy_price": 5535, "multi_buy_qty": 2, "discount_rate": 0.10,
     "barcode": None},
    {"category": "라면", "company": "하림산업", "brand": "더미식", "product_group": "더미식 장인라면",
     "target_segment": "성인",
     "sku": "하림 더미식 장인라면 얼큰한맛", "sku_name": "하림 더미식 장인라면 얼큰한맛",
     "spec": "4입", "ea": "4입", "storage_type": "상온",
     "price": 6600, "multi_buy_price": None, "multi_buy_qty": None, "discount_rate": None,
     "barcode": None},
    {"category": "라면", "company": "하림산업", "brand": "더미식", "product_group": "더미식 장인라면",
     "target_segment": "성인",
     "sku": "하림 더미식 장인라면 담백한맛", "sku_name": "하림 더미식 장인라면 담백한맛",
     "spec": "4입", "ea": "4입", "storage_type": "상온",
     "price": 6600, "multi_buy_price": None, "multi_buy_qty": None, "discount_rate": None,
     "barcode": None},
    {"category": "라면", "company": "하림산업", "brand": "더미식", "product_group": "더미식 장인라면",
     "target_segment": "성인",
     "sku": "하림 더미식 장인라면 맵싸한맛", "sku_name": "하림 더미식 장인라면 맵싸한맛",
     "spec": "4입", "ea": "4입", "storage_type": "상온",
     "price": 6600, "multi_buy_price": None, "multi_buy_qty": None, "discount_rate": None,
     "barcode": None},
    {"category": "라면", "company": "하림산업", "brand": "더미식", "product_group": "더미식 오징어라면",
     "target_segment": "성인",
     "sku": "하림 더미식 오징어라면", "sku_name": "하림 더미식 오징어라면",
     "spec": "4입", "ea": "4입", "storage_type": "상온",
     "price": 7480, "multi_buy_price": None, "multi_buy_qty": None, "discount_rate": None,
     "barcode": None},
    {"category": "라면", "company": "풀무원", "brand": "서울라면", "product_group": "서울라면",
     "target_segment": "성인",
     "sku": "풀무원 자연건면 로스팅 서울라면", "sku_name": "풀무원 자연건면 로스팅 서울라면",
     "spec": "4입", "ea": "4입", "storage_type": "상온",
     "price": 5450, "multi_buy_price": None, "multi_buy_qty": None, "discount_rate": None,
     "barcode": None},

    # ── 라면 (상온) — 2026.07.27 추가 반영 (매니저 제공 엑셀 기준) ──
    # ⚠️ 아래 5개는 위 6개(실사 가격표 대조 완료)와 달리 이번 매장에서 직접 확인된
    # 항목이 아님 — 웹 검색으로 실존 제품 여부만 교차 확인한 상태. 실제 매대에서
    # 가격표/제품 육안 대조 전까지는 "미검증"으로 취급할 것.
    # - 하림 맛나면: 실존 확인됨. 단, 제조사가 "하림"(하림산업 아님)으로 표기된
    #   자료가 있어 company="하림산업"이 맞는지 재확인 필요.
    # - 신라면 볶음면: 실존 확인됨. 3,980원이 4입 정가인지 행사가인지 확인 필요.
    # - 하림 훌라면: 실존 확인됨(2026년 상반기 하와이 역수입 출시, 하림산업 확인).
    {"category": "라면", "company": "하림산업", "brand": "푸디버디", "product_group": "푸디버디 빨강라면",
     "target_segment": "어린이",
     "sku": "푸디버디 빨강라면", "sku_name": "푸디버디 빨강라면", "spec": "4입", "ea": "4입",
     "storage_type": "상온",
     "price": 6800, "multi_buy_price": None, "multi_buy_qty": None, "discount_rate": None,
     "barcode": None},
    {"category": "라면", "company": "하림산업", "brand": "푸디버디", "product_group": "푸디버디 하양라면",
     "target_segment": "어린이",
     "sku": "푸디버디 하양라면", "sku_name": "푸디버디 하양라면", "spec": "4입", "ea": "4입",
     "storage_type": "상온",
     "price": 6800, "multi_buy_price": None, "multi_buy_qty": None, "discount_rate": None,
     "barcode": None},
    {"category": "라면", "company": "하림산업", "brand": "푸디버디", "product_group": "푸디버디 간장비빔면",
     "target_segment": "어린이",
     "sku": "푸디버디 꼬소한 김 간장비빔면", "sku_name": "푸디버디 꼬소한 김 간장비빔면",
     "spec": "4입", "ea": "4입", "storage_type": "상온",
     "price": 6800, "multi_buy_price": None, "multi_buy_qty": None, "discount_rate": None,
     "barcode": None},
    {"category": "라면", "company": "하림산업", "brand": "하림", "product_group": "맛나면",
     "target_segment": "성인",
     "sku": "하림 맛나면", "sku_name": "하림 맛나면", "spec": "4입", "ea": "4입",
     "storage_type": "상온",
     "price": 4800, "multi_buy_price": None, "multi_buy_qty": None, "discount_rate": None,
     "barcode": None},
    {"category": "라면", "company": "하림산업", "brand": "하림", "product_group": "훌라면",
     "target_segment": "성인",
     "sku": "하림 훌라면", "sku_name": "하림 훌라면", "spec": "4입", "ea": "4입",
     "storage_type": "상온",
     "price": 5600, "multi_buy_price": None, "multi_buy_qty": None, "discount_rate": None,
     "barcode": None},
    {"category": "라면", "company": "농심", "brand": "신라면", "product_group": "신라면 볶음면",
     "target_segment": "성인",
     "sku": "신라면 볶음면", "sku_name": "신라면 볶음면", "spec": "4입", "ea": "4입",
     "storage_type": "상온",
     "price": 3980, "multi_buy_price": None, "multi_buy_qty": None, "discount_rate": None,
     "barcode": None},
]


def get_catalog_names():
    """rapidfuzz 매칭용 검색 대상 문자열 리스트 반환.
    brand가 이미 sku(sku_name) 문자열 안에 포함돼 있으면(예: 라면 카테고리처럼
    가격표 전체 텍스트를 sku로 쓰는 경우) 중복 접두어를 붙이지 않는다.
    """
    names = []
    for item in CATALOG:
        text = item.get("sku") or item.get("sku_name", "")
        brand = item.get("brand", "")
        if brand and brand not in text:
            names.append(f"{brand} {text}")
        else:
            names.append(text)
    return names


def get_catalog_by_index(idx):
    return CATALOG[idx]
