import requests
import os
import json
from datetime import datetime, timedelta

# ==================== 설정 ====================
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
APP_KEY = os.getenv("APP_KEY")
APP_SECRET = os.getenv("APP_SECRET")
THRESHOLD = float(os.getenv("THRESHOLD", "5"))
# ============================================

def get_futures_code():
    """원달러 선물 근월물 종목코드 자동 계산 (매월 3번째 월요일 만기)"""
    now = datetime.now()
    year = now.year
    month = now.month

    def third_monday(y, m):
        first_day = datetime(y, m, 1)
        days_until_monday = (7 - first_day.weekday()) % 7
        first_monday = first_day + timedelta(days=days_until_monday)
        return first_monday + timedelta(weeks=2)

    expiry = third_monday(year, month)

    # 만기일이 이미 지났으면 다음 달 월물로
    if now.date() > expiry.date():
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1

    return f"101W{month:02d}"

def get_access_token():
    """한국투자증권 액세스 토큰 발급"""
    url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
    headers = {"content-type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
    }
    resp = requests.post(url, headers=headers, json=body)
    response_data = resp.json()
    print("토큰 응답:", json.dumps(response_data, indent=2, ensure_ascii=False))

    if "access_token" in response_data:
        return response_data["access_token"]
    else:
        raise Exception(f"토큰 발급 실패: {response_data}")

def get_usd_futures_price():
    """원달러 선물 현재가 조회"""
    access_token = get_access_token()
    futures_code = get_futures_code()
    print(f"조회 종목코드: {futures_code}")

    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-futureoption/v1/quotations/inquire-price"

    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {access_token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHKIF03010100",
        "custtype": "P",
        "tr_cont": ""
    }

    params = {"FUT_ITEM_CD": futures_code}

    resp = requests.get(url, headers=headers, params=params)

    # 디버깅용 출력
    print(f"HTTP 상태코드: {resp.status_code}")
    print(f"응답 raw: '{resp.text[:300]}'")

    if not resp.text:
        raise Exception("응답이 비어있음 — 엔드포인트 또는 종목코드 확인 필요")

    data = resp.json()
    print("선물 가격 응답:", json.dumps(data, indent=2, ensure_ascii=False))

    if data.get("rt_cd") == "0" and "output" in data:
        output = data["output"]
        price_str = output.get("prpr") or output.get("stck_prpr") or output.get("last") or "0"
        price = float(price_str)
        return round(price, 2)
    else:
        raise Exception(f"가격 조회 실패: {data}")

def get_bithumb_usdt():
    """빗썸 USDT/KRW 현재가 조회"""
    url = "https://api.bithumb.com/public/ticker/USDT_KRW"
    resp = requests.get(url)
    data = resp.json()

    if data.get("status") != "0000":
        raise Exception(f"빗썸 API 오류: {data}")

    return float(data["data"]["closing_price"])

def send_discord(difference, bithumb_usdt, futures_price):
    """디스코드 웹훅으로 알람 전송"""
    message = f"""🚨 **테더 차이 알람!**

빗썸 USDT: **{bithumb_usdt}원**
원달러 선물: **{futures_price}원**
**차이: {difference}원** (기준: {THRESHOLD}원 이상)"""

    resp = requests.post(WEBHOOK_URL, json={"content": message})
    if resp.status_code not in (200, 204):
        raise Exception(f"디스코드 전송 실패: {resp.status_code} {resp.text}")

# ==================== 실행 ====================
try:
    bithumb_usdt = get_bithumb_usdt()
    futures_price = get_usd_futures_price()
    difference = round(bithumb_usdt - futures_price, 2)

    print(f"✅ 빗썸 USDT: {bithumb_usdt} | 원달러 선물: {futures_price} | 차이: {difference}원")

    if difference >= THRESHOLD:
        send_discord(difference, bithumb_usdt, futures_price)
        print("✅ 알람 전송 완료")
    else:
        print("ℹ️ 알람 조건 미달")

except Exception as e:
    print("❌ 오류 발생:", str(e))
