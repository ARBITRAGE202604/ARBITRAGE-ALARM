네, 전체 코드 드립니다. 토큰 캐싱도 추가했어요 (1분 발급 제한 대응).

```python
import requests
import os
import json
from datetime import datetime, timedelta

# ==================== 설정 ====================
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
APP_KEY = os.getenv("APP_KEY")
APP_SECRET = os.getenv("APP_SECRET")
THRESHOLD = float(os.getenv("THRESHOLD", "5"))

BASE_URL = "https://openapi.koreainvestment.com:9443"
TOKEN_FILE = "token_cache.json"
# ============================================


def get_third_monday(year, month):
    """해당 월의 세번째 월요일 = USD선물 최종거래일"""
    first = datetime(year, month, 1)
    days_until_monday = (0 - first.weekday()) % 7
    first_monday = first + timedelta(days=days_until_monday)
    return first_monday + timedelta(days=14)


def get_usd_futures_code():
    """미국달러선물 근월물 종목코드 (매월물)"""
    now = datetime.now()
    year, month = now.year, now.month

    # 이번 달 세번째 월요일(최종거래일) 지났으면 다음 월물로 롤오버
    expiry = get_third_monday(year, month)
    if now.date() > expiry.date():
        month += 1
        if month > 12:
            month = 1
            year += 1

    # 월물 코드: 1~9월=1~9, 10월=A, 11월=B, 12월=C
    month_code = {1: '1', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6',
                  7: '7', 8: '8', 9: '9', 10: 'A', 11: 'B', 12: 'C'}[month]

    yy = year % 100
    code = f"175T{month_code}{yy:02d}"  # 예: 175T426 = 2026년 4월물
    print(f"📌 USD선물 종목코드: {code} (만기: {expiry.strftime('%Y-%m-%d')})")
    return code


def get_access_token():
    """토큰 캐싱 (유효하면 재사용, 1분 발급 제한 대응)"""
    # 캐시된 토큰 확인
    if os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, "r") as f:
                cache = json.load(f)
            expires_at = datetime.fromisoformat(cache["expires_at"])
            if datetime.now() < expires_at:
                print("♻️ 캐시된 토큰 사용")
                return cache["access_token"]
        except Exception:
            pass

    # 신규 발급
    url = f"{BASE_URL}/oauth2/tokenP"
    body = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
    }
    resp = requests.post(url, json=body,
                         headers={"content-type": "application/json"})
    resp.raise_for_status()
    data = resp.json()

    token = data["access_token"]
    # 만료시간 저장 (기본 24시간, 안전하게 23시간으로 설정)
    expires_at = datetime.now() + timedelta(hours=23)
    with open(TOKEN_FILE, "w") as f:
        json.dump({
            "access_token": token,
            "expires_at": expires_at.isoformat()
        }, f)
    print("🆕 신규 토큰 발급")
    return token


def get_usd_futures_price():
    token = get_access_token()
    code = get_usd_futures_code()

    url = f"{BASE_URL}/uapi/domestic-futureoption/v1/quotations/inquire-price"
    headers = {
        "content-type": "application/json; charset=utf-8",
        "authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "FHMIF10000000",
        "custtype": "P"
    }
    params = {
        "FID_COND_MRKT_DIV_CODE": "F",
        "FID_INPUT_ISCD": code
    }

    resp = requests.get(url, headers=headers, params=params)
    print(f"Status: {resp.status_code}")
    data = resp.json()

    if data.get("rt_cd") != "0":
        print(f"Response: {data}")
        raise Exception(f"API 오류: {data.get('msg1')}")

    output = data["output"]
    # 필드명이 API 버전에 따라 다를 수 있어 여러개 시도
    price_str = (output.get("futs_prpr")
                 or output.get("prpr")
                 or output.get("stck_prpr"))
    if not price_str:
        print(f"Output: {output}")
        raise Exception("가격 필드를 찾을 수 없음")

    price = float(price_str)
    print(f"✅ USD선물 가격: {price}원")
    return round(price, 2)


def get_bithumb_usdt():
    url = "https://api.bithumb.com/public/ticker/USDT_KRW"
    data = requests.get(url).json()
    price = float(data["data"]["closing_price"])
    print(f"✅ 빗썸 USDT 가격: {price}원")
    return price


def send_discord(difference, bithumb, futures):
    sign = "📈" if difference > 0 else "📉"
    message = (f"🚨 **테더 차이 알람!** {sign}\n\n"
               f"빗썸 USDT : **{bithumb:,}원**\n"
               f"USD 선물 : **{futures:,}원**\n"
               f"**차이 : {difference}원** (기준: {THRESHOLD}원 이상)")
    requests.post(WEBHOOK_URL, json={"content": message})


# ==================== 실행 ====================
if __name__ == "__main__":
    try:
        bithumb = get_bithumb_usdt()
        futures = get_usd_futures_price()
        diff = round(bithumb - futures, 2)

        print(f"🎯 빗썸 {bithumb} | 선물 {futures} | 차이 {diff}원")

        if abs(diff) >= THRESHOLD:
            send_discord(diff, bithumb, futures)
            print("✅ 알람 전송 완료")
        else:
            print("ℹ️ 기준 미달 - 알람 미전송")

    except Exception as e:
        print(f"❌ 오류: {e}")
        # 디스코드로 오류 알림 (선택)
        if WEBHOOK_URL:
            try:
                requests.post(WEBHOOK_URL,
                              json={"content": f"⚠️ 스크립트 오류: {str(e)[:500]}"})
            except Exception:
                pass
```

## 🔑 주요 변경사항

| 항목 | 내용 |
|------|------|
| **종목코드** | `175T` + 월물코드(1자) + 연도(2자), 세번째 월요일 기준 롤오버 |
| **엔드포인트** | `domestic-futureoption` (하이픈 수정) |
| **파라미터** | `FID_COND_MRKT_DIV_CODE=F`, `FID_INPUT_ISCD=종목코드` |
| **tr_id** | `FHMIF10000000` (선물옵션 시세) |
| **토큰 캐싱** | `
