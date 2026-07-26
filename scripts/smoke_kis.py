"""KIS 인증·조회 스모크 테스트.

실행: uv run python scripts/smoke_kis.py [--env real|paper]
조회 전용 — 주문은 일절 나가지 않는다.
"""

import argparse
import sys
from datetime import date, timedelta

from broker_kis import KISApiError, KISBroker, KISSettings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", choices=["real", "paper"], default="real")
    args = parser.parse_args()

    print(f"=== KIS 스모크 테스트 (env={args.env}) ===\n")

    # 1. 설정 로드
    settings = KISSettings.load(args.env)
    print(f"[1/5] 설정 로드 OK — 계좌 {settings.account}-{settings.product}, 서버 {settings.base_url}")

    # 2. 토큰 발급
    broker = KISBroker(env=args.env, settings=settings)
    token = broker.client.tokens.get_token()
    print(f"[2/5] 토큰 발급 OK — {token[:12]}... (캐시: D:/kis/config/tokens)")

    # 3. 현재가 조회 (삼성전자)
    quote = broker.get_quote("005930")
    print(f"[3/5] 현재가 조회 OK — 삼성전자 {quote.price:,}원")

    # 4. 일봉 조회
    candles = broker.get_daily_candles("005930", date.today() - timedelta(days=14), date.today())
    print(f"[4/5] 일봉 조회 OK — 최근 {len(candles)}건, 마지막: {candles[-1].ts.date()} 종가 {candles[-1].close:,}원")

    # 5. 잔고 조회 — 계좌번호 검증
    try:
        balance = broker.get_balance()
        print(f"[5/5] 잔고 조회 OK — 예수금 {balance.cash:,}원 / 총평가 {balance.total_value:,}원")
    except KISApiError as e:
        print(f"[5/5] 잔고 조회 실패 (계좌번호 확인 필요): {e}")

    print("\n✅ 전체 통과")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ 실패: {type(e).__name__}: {e}")
        sys.exit(1)
