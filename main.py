import requests
import os
import re
from datetime import datetime

# ==================== 설정 ====================
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
THRESHOLD = float(os.getenv("THRESHOLD", "5"))
# ============================================


def get_google_usd_krw():
    """구글 파이낸스에서 USD/KRW 환율 크롤링"""
    url = "https://www.google.com/finance/quote/USD-KRW"
    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/120.0.0.0 Safari/537.36")
    }
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()

    # data-last-price="1234.56" 패턴 추출
    match = re.search(r'data-last-price="([\d.]+)"', resp.text)
    if not match:
        raise Exception("구글 환율 파싱 실패 - 페이지 구조 변경 가능성")

    price = float(match.group(1))
    print(f"✅ 구글 USD/KRW 환율: {price:,}원")
    return round(price, 2)


def get_bithumb_usdt():
    """빗썸 USDT/KRW 현재가"""
    url = "https://api.bithumb.com/public/ticker/USDT_KRW"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    price = float(data["data"]["closing_price"])
    print(f"✅ 빗썸 USDT 가격: {price:,}원")
    return price


def send_discord(difference, bithumb, usd_krw):
    """디스코드 웹훅 알람 전송"""
    sign = "📈" if difference > 0 else "📉"
    label = "김프" if difference > 0 else "역프"
    
    message = (f"🚨 **테더 차이 알람!** {sign} ({label})\n\n"
               f"빗썸 USDT : **{bithumb:,}원**\n"
               f"USD/KRW 환율 : **{usd_krw:,}원**\n"
               f"**차이 : {difference}원** (기준: ±{THRESHOLD}원)\n"
               f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    requests.post(WEBHOOK_URL, json={"content": message}, timeout=10)


# ==================== 실행 ====================
if __name__ == "__main__":
    try:
        bithumb = get_bithumb_usdt()
        usd_krw = get_google_usd_krw()
        diff = round(bithumb - usd_krw, 2)

        print(f"🎯 빗썸 {bithumb:,} | 환율 {usd_krw:,} | 차이 {diff}원")

        if abs(diff) >= THRESHOLD:
            send_discord(diff, bithumb, usd_krw)
            print("✅ 알람 전송 완료")
        else:
            print(f"ℹ️ 기준({THRESHOLD}원) 미달 - 알람 미전송")

    except Exception as e:
        print(f"❌ 오류: {e}")
        if WEBHOOK_URL:
            try:
                requests.post(
                    WEBHOOK_URL,
                    json={"content": f"⚠️ 스크립트 오류: {str(e)[:500]}"},
                    timeout=10
                )
            except Exception:
                pass
