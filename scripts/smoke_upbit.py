"""업비트 인증·조회 스모크 테스트.

실행: uv run python scripts/smoke_upbit.py
조회 전용 — 주문은 일절 나가지 않는다.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta

from broker_upbit import UpbitApiError, UpbitBroker, UpbitSettings, align_price


def main():
    print("=== 업비트 스모크 테스트 ===\n")

    # 1~2. 공개 API는 인증 없이도 되지만, 설정·인증부터 확인
    settings = UpbitSettings.load()
    print(f"[1/6] 설정 로드 OK — access_key {settings.access_key[:8]}…")

    broker = UpbitBroker(settings)
    markets = broker.list_krw_markets()
    print(f"[2/6] KRW 마켓 조회 OK — {len(markets)}종목 (예: {', '.join(markets[:5])})")

    # 3. 현재가
    quote = broker.get_quote("KRW-BTC")
    print(f"[3/6] 현재가 조회 OK — BTC {quote.price:,}원")

    # 4. 일봉
    daily = broker.get_daily_candles("KRW-BTC", date.today() - timedelta(days=10), date.today())
    print(f"[4/6] 일봉 조회 OK — {len(daily)}건, 마지막 {daily[-1].ts.date()} 종가 {daily[-1].close:,}")

    # 5. 분봉 (단타봇 주력)
    m5 = broker.get_minute_candles("KRW-BTC", unit=5, count=100)
    print(f"[5/6] 5분봉 조회 OK — {len(m5)}건, 마지막 {m5[-1].ts}")

    # 6. 인증 필요: 잔고
    try:
        balance = broker.get_balance()
        positions = broker.get_positions()
        print(f"[6/6] 잔고 조회 OK (인증 성공) — 원화 {balance.cash:,}원, 보유코인 {len(positions)}종")
        for p in positions[:5]:
            print(f"        {p.symbol}: {p.quantity} @ 평단 {p.avg_price:,} (현재 {p.current_price:,})")
    except UpbitApiError as e:
        print(f"[6/6] 잔고 조회 실패 — {e}")
        print("      → 키 권한(자산 조회) 또는 허용 IP 설정을 확인하세요")
        return

    # 참고: 호가단위 정렬 확인
    print(f"\n[참고] 호가단위 정렬: {quote.price:,} → 지정가 {align_price(quote.price):,}")
    rules = broker.get_market_rules("KRW-BTC")
    print(f"[참고] 시장 규칙: 최소주문 {rules.min_order_value:,}원, 수수료 {rules.fee_rate*100}%, "
          f"거래세 {rules.sell_tax_rate*100}%, 24시간={rules.open_time is None}")
    print("\n✅ 전체 통과")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ 실패: {type(e).__name__}: {e}")
        sys.exit(1)
