import requests
import os
import json

# ==================== 설정 ====================
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
APP_KEY = os.getenv("APP_KEY")
APP_SECRET = os.getenv("APP_SECRET")
THRESHOLD = float(os.getenv("THRESHOLD", "5"))
# ============================================

def get_access_token():
    """한국투자증권 토큰 발급 (수정 버전)"""
    url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
    
    headers = {
        "content-type": "application/json"
    }
    
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
    """원달러 선물 가격 가져오기"""
    access_token = get_access_token()
    
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-future-option/v1/quotations"
    
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {access_token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FUTU",           # 국내선물호가
        "tr_cont": ""
    }
    
    params = {
        "futCd": "USD"             # 달러선물
    }
    
    resp = requests.get(url, headers=headers, params=params)   # GET으로 변경
    data = resp.json()
    
    print("선물 가격 응답:", json.dumps(data, indent=2, ensure_ascii=False))
    
    if "output" in data:
        price = float(data["output"].get("stck_prpr") or data["output"].get("prpr") or 0)
        return round(price, 2)
    else:
        raise Exception(f"가격 조회 실패: {data}")

def get_bithumb_usdt():
    url = "https://api.bithumb.com/public/ticker/USDT_KRW"
    data = requests.get(url).json()
    return float(data["data"]["closing_price"])

def send_discord(difference, bithumb_usdt, futures_price):
    message = f"""🚨 **테더 차이 알람!**
    
빗썸 USDT: **{bithumb_usdt}원**
원달러 선물: **{futures_price}원**
**차이: {difference}원** (기준: {THRESHOLD}원 이상)"""
    
    requests.post(WEBHOOK_URL, json={"content": message})

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
