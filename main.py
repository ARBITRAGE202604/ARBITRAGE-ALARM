import requests
import os

# ==================== 설정 ====================
WEBHOOK_URL = os.getenv("WEBHOOK_URL")   # 여기 건드리지 마세요

THRESHOLD = 3        # ← 여기 숫자만 바꾸세요! (오늘 3원, 내일 5원, 0원 등)
# ============================================

def get_bithumb_usdt():
    url = "https://api.bithumb.com/public/ticker/USDT_KRW"
    data = requests.get(url).json()
    return float(data['data']['closing_price'])

def get_usd_krw():
    url = "https://api.exchangerate-api.com/v4/latest/USD"
    data = requests.get(url).json()
    return float(data['rates']['KRW'])

def send_alert(difference):
    message = f"""🚨 **테더 차이 알람!**
    
빗썸 USDT: **{bithumb_usdt}원**
현재 환율: **{usd_krw}원**
**차이: {difference}원** (기준: {THRESHOLD}원 이상)"""
    
    requests.post(WEBHOOK_URL, json={"content": message})

# 메인 실행
try:
    bithumb_usdt = get_bithumb_usdt()
    usd_krw = get_usd_krw()
    difference = round(bithumb_usdt - usd_krw, 2)
    
    print(f"빗썸 USDT: {bithumb_usdt} | 환율: {usd_krw} | 차이: {difference}원")
    
    if difference >= THRESHOLD:
        send_alert(difference)
        print("✅ 알람 전송됨")
    else:
        print("알람 조건 미달")
        
except Exception as e:
    print("오류:", e)
