import requests
import os
import json
from datetime import datetime

# ==================== 설정 ====================
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
APP_KEY = os.getenv("APP_KEY")
APP_SECRET = os.getenv("APP_SECRET")
THRESHOLD = float(os.getenv("THRESHOLD", "5"))
# ============================================

def get_futures_code():
    """원달러 선물 근월물 종목코드"""
    now = datetime.now()
    month = now.month
    if now.day >= 18:   # 안전하게 다음 월물로 넘김
        month += 1
        if month > 12:
            month = 1
    code = f"101W{month:02d}"
    print(f"📌 사용 종목코드: {code}")
    return code

def get_access_token():
    url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
    headers = {"content-type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
    }
    resp = requests.post(url, headers=headers, json=body)
    data = resp.json()
    if "access_token" in data:
        return data["access_token"]
    else:
        raise Exception(f"토큰 발급 실패: {data}")

def get_usd_futures_price():
    access_token = get_access_token()
    futures_code = get_futures_code()
    
    # 🔥 가장 성공률 높은 엔드포인트로 변경
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-future-option/v1/quotations/inquire-price"
    
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {access_token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHKIF03010100",     # 국내선물 현재가 전용 tr_id
        "tr_cont": ""
    }
    
    params = {
        "futCd": futures_code
    }
    
    resp = requests.get(url, headers=headers, params=params)
    
    print(f"📡 HTTP Status: {resp.status_code}")
    print(f"📄 Raw Response: {resp.text[:700]}...")
    
    if resp.status_code != 200:
        raise Exception(f"HTTP 오류 {resp.status_code}: {resp.text}")
    
    data = resp.json()
    
    if data.get("rt_cd") == "0" and "output" in data:
        output = data["output"]
        price = float(output.get("prpr") or output.get("stck_prpr") or 0)
        print(f"✅ 원달러 선물 가격: {price:,}원")
        return round(price, 2)
    else:
        raise Exception(f"가격 조회 실패: {data.get('msg1', data)}")

def get_bithumb_usdt():
    url = "https://api.bithumb.com/public/ticker/USDT_KRW"
    resp = requests.get(url)
    data = resp.json()
    if data.get("status") != "0000":
        raise Exception(f"빗썸 오류: {data}")
    return float(data["data"]["closing_price"])

def send_discord(difference, bithumb_usdt, futures_price):
    message = f"""🚨 **테더 차이 알람!**
    
빗썸 USDT : **{bithumb_usdt:,}원**
원달러 선물 : **{futures_price:,}원**
**차이 : {difference}원** (기준: {THRESHOLD}원 이상)"""
    requests.post(WEBHOOK_URL, json={"content": message})

# ==================== 실행 ====================
try:
    bithumb_usdt = get_bithumb_usdt()
    futures_price = get_usd_futures_price()
    difference = round(bithumb_usdt - futures_price, 2)
    
    print(f"🎯 최종 → 빗썸 {bithumb_usdt:,} | 선물 {futures_price:,} | 차이 {difference}원")
    
    if difference >= THRESHOLD:
        send_discord(difference, bithumb_usdt, futures_price)
        print("✅ 알람 전송 완료")
    else:
        print(f"ℹ️ 기준 미달 ({difference}원)")
        
except Exception as e:
    print(f"❌ 오류: {str(e)}")
