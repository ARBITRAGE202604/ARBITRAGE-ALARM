import requests
import os

# ==================== 설정 ====================
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
APP_KEY = os.getenv("APP_KEY")
APP_SECRET = os.getenv("APP_SECRET")
THRESHOLD = float(os.getenv("THRESHOLD", "5"))   # ← 여기서 기본값 5원, Secret으로도 변경 가능
# ============================================

def get_access_token():
    """한국투자증권 토큰 발급"""
    url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
    data = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
    }
    resp = requests.post(url, json=data)
    return resp.json()["access_token"]

def get_usd_futures_price():
    """한국투자증권 원달러 선물 가격 가져오기"""
    access_token = get_access_token()
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-future-option/v1/quotations"
    
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {access_token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FUTU"          # 국내선물 현재가
    }
    
    body = {"futCd": "USD"}      # 미국달러선물 코드
    
    resp = requests.post(url, headers=headers, json=body)
    data = resp.json().get("output", {})
    
    # 가격 필드 (실제 응답에 따라 stck_prpr 또는 bspr 등)
    price = float(data.get("stck_prpr") or data.get("prpr") or 0)
    return round(price, 2)

def get_bithumb_usdt():
    """빗썸 USDT/KRW 가격"""
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
    
    print(f"빗썸 USDT: {bithumb_usdt} | 원달러 선물: {futures_price} | 차이: {difference}원")
    
    if difference >= THRESHOLD:
        send_discord(difference, bithumb_usdt, futures_price)
        print("✅ 알람 전송 완료")
    else:
        print("알람 조건 미달")
        
except Exception as e:
    print("오류 발생:", e)
