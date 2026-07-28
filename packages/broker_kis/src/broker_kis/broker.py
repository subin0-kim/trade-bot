"""KISBroker — trading_core.Broker 구현 (국내주식 현물).

엔드포인트/tr_id/파라미터는 공식 샘플 open-trading-api examples_llm 기준.
주의사항은 wiki/shared/brokers/kis/api-notes.md 참고.
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from trading_core.models import (
    Balance,
    Candle,
    MarketRules,
    Order,
    OrderRequest,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    Quote,
)

from .client import KISClient
from .config import KISSettings


def _dec(value: str | None, default: str = "0") -> Decimal:
    s = (value or default).strip() or default
    return Decimal(s)


class KISBroker:
    """국내주식 현물 브로커. env='paper'면 모의투자 서버 사용."""

    def __init__(self, env: str = "paper", settings: KISSettings | None = None):
        self.settings = settings or KISSettings.load(env)
        self.client = KISClient(self.settings)

    # ------------------------------------------------------------------ 시세
    def get_quote(self, symbol: str) -> Quote:
        data = self.client.get(
            "/uapi/domestic-stock/v1/quotations/inquire-price",
            "FHKST01010100",
            {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": symbol},
        )
        return Quote(
            symbol=symbol,
            price=_dec(data["output"]["stck_prpr"]),
            ts=datetime.now(),
        )

    def is_open_day(self, d: date) -> bool | None:
        """국내 개장일 여부 (CTCA0903R). 실패 시 None.

        ⚠️ 원장 연동 서비스라 공식 가이드가 '1일 1회 호출'을 권고 —
        호출부는 반드시 일 단위로 캐시할 것 (bot_swing.holiday 참조).
        """
        try:
            data = self.client.get(
                "/uapi/domestic-stock/v1/quotations/chk-holiday",
                "CTCA0903R",
                {"BASS_DT": d.strftime("%Y%m%d"), "CTX_AREA_FK": "", "CTX_AREA_NK": ""},
            )
        except Exception:
            return None
        for row in data.get("output", []):
            if row.get("bass_dt") == d.strftime("%Y%m%d"):
                return row.get("opnd_yn") == "Y"
        return None

    def get_daily_candles(
        self, symbol: str, start: date, end: date, period: str = "D"
    ) -> list[Candle]:
        """period: D(일) / W(주) / M(월). 수정주가 기준, 최대 100건/호출."""
        data = self.client.get(
            "/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice",
            "FHKST03010100",
            {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": symbol,
                "FID_INPUT_DATE_1": start.strftime("%Y%m%d"),
                "FID_INPUT_DATE_2": end.strftime("%Y%m%d"),
                "FID_PERIOD_DIV_CODE": period,
                "FID_ORG_ADJ_PRC": "0",  # 0: 수정주가
            },
        )
        candles = []
        for row in data.get("output2", []):
            if not row.get("stck_bsop_date"):
                continue
            candles.append(
                Candle(
                    ts=datetime.strptime(row["stck_bsop_date"], "%Y%m%d"),
                    open=_dec(row["stck_oprc"]),
                    high=_dec(row["stck_hgpr"]),
                    low=_dec(row["stck_lwpr"]),
                    close=_dec(row["stck_clpr"]),
                    volume=_dec(row["acml_vol"]),
                )
            )
        return sorted(candles, key=lambda c: c.ts)

    def get_minute_candles(self, symbol: str, to_time: str | None = None) -> list[Candle]:
        """당일 분봉. to_time(HHMMSS) 기준 직전 최대 30건 반환."""
        data = self.client.get(
            "/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice",
            "FHKST03010200",
            {
                "FID_COND_MRKT_DIV_CODE": "J",
                "FID_INPUT_ISCD": symbol,
                "FID_INPUT_HOUR_1": to_time or datetime.now().strftime("%H%M%S"),
                "FID_PW_DATA_INCU_YN": "Y",
                "FID_ETC_CLS_CODE": "",
            },
        )
        candles = []
        for row in data.get("output2", []):
            if not row.get("stck_bsop_date"):
                continue
            candles.append(
                Candle(
                    ts=datetime.strptime(
                        row["stck_bsop_date"] + row["stck_cntg_hour"], "%Y%m%d%H%M%S"
                    ),
                    open=_dec(row["stck_oprc"]),
                    high=_dec(row["stck_hgpr"]),
                    low=_dec(row["stck_lwpr"]),
                    close=_dec(row["stck_prpr"]),  # 분봉의 종가 = 체결가
                    volume=_dec(row["cntg_vol"]),
                )
            )
        return sorted(candles, key=lambda c: c.ts)

    def get_index_daily_candles(
        self, index_code: str, start: date, end: date, period: str = "D"
    ) -> list[Candle]:
        """업종/지수 일봉. index_code: 0001 코스피, 1001 코스닥, 2001 코스피200 등.

        지수는 거래량 개념이 거래대금과 혼재하므로 volume은 acml_vol 그대로 담는다.
        """
        data = self.client.get(
            "/uapi/domestic-stock/v1/quotations/inquire-daily-indexchartprice",
            "FHKUP03500100",
            {
                "FID_COND_MRKT_DIV_CODE": "U",
                "FID_INPUT_ISCD": index_code,
                "FID_INPUT_DATE_1": start.strftime("%Y%m%d"),
                "FID_INPUT_DATE_2": end.strftime("%Y%m%d"),
                "FID_PERIOD_DIV_CODE": period,
            },
        )
        candles = []
        for row in data.get("output2", []):
            if not row.get("stck_bsop_date"):
                continue
            candles.append(
                Candle(
                    ts=datetime.strptime(row["stck_bsop_date"], "%Y%m%d"),
                    open=_dec(row["bstp_nmix_oprc"]),
                    high=_dec(row["bstp_nmix_hgpr"]),
                    low=_dec(row["bstp_nmix_lwpr"]),
                    close=_dec(row["bstp_nmix_prpr"]),
                    volume=_dec(row.get("acml_vol")),
                )
            )
        return sorted(candles, key=lambda c: c.ts)

    def get_market_rules(self, symbol: str) -> MarketRules:
        return MarketRules(
            symbol=symbol,
            min_order_value=Decimal(0),
            quantity_step=Decimal(1),          # 국내주식은 1주 단위
            open_time=time(9, 0),
            close_time=time(15, 30),
            fee_rate=Decimal("0.00015"),       # 위탁수수료 (계좌 조건에 따라 다름)
            sell_tax_rate=Decimal("0.0018"),   # 증권거래세+농특세 (2025~ 코스피/코스닥 0.18%)
        )

    # ------------------------------------------------------------------ 계좌
    def _inquire_balance(self) -> dict:
        return self.client.get(
            "/uapi/domestic-stock/v1/trading/inquire-balance",
            "TTTC8434R",
            {
                "CANO": self.settings.account,
                "ACNT_PRDT_CD": self.settings.product,
                "AFHR_FLPR_YN": "N",
                "OFL_YN": "",
                "INQR_DVSN": "02",
                "UNPR_DVSN": "01",
                "FUND_STTL_ICLD_YN": "N",
                "FNCG_AMT_AUTO_RDPT_YN": "N",
                "PRCS_DVSN": "00",
                "CTX_AREA_FK100": "",
                "CTX_AREA_NK100": "",
            },
        )

    def get_balance(self) -> Balance:
        data = self._inquire_balance()
        summary = data["output2"][0]
        return Balance(
            cash=_dec(summary.get("dnca_tot_amt")),               # 예수금
            available_cash=_dec(summary.get("prvs_rcdl_excc_amt")),  # D+2 예수금
            total_value=_dec(summary.get("tot_evlu_amt")),        # 총평가금액
        )

    def get_positions(self) -> list[Position]:
        data = self._inquire_balance()
        positions = []
        for row in data.get("output1", []):
            qty = _dec(row.get("hldg_qty"))
            if qty <= 0:
                continue
            positions.append(
                Position(
                    symbol=row["pdno"],
                    name=row.get("prdt_name", ""),
                    quantity=qty,
                    avg_price=_dec(row.get("pchs_avg_pric")),
                    current_price=_dec(row.get("prpr")),
                )
            )
        return positions

    def get_open_orders(self) -> list[Order]:
        """정정/취소 가능 주문(=미체결) 조회. ※ 모의투자 미지원 TR."""
        data = self.client.get(
            "/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl",
            "TTTC0084R",
            {
                "CANO": self.settings.account,
                "ACNT_PRDT_CD": self.settings.product,
                "INQR_DVSN_1": "1",  # 주문순
                "INQR_DVSN_2": "0",  # 전체
                "CTX_AREA_FK100": "",
                "CTX_AREA_NK100": "",
            },
        )
        orders = []
        for row in data.get("output", []):
            if not row.get("odno"):
                continue
            qty = _dec(row.get("ord_qty"))
            filled = _dec(row.get("tot_ccld_qty"))
            orders.append(
                Order(
                    order_id=row["odno"],
                    symbol=row["pdno"],
                    side=OrderSide.SELL if row.get("sll_buy_dvsn_cd") == "01" else OrderSide.BUY,
                    quantity=qty,
                    filled_quantity=filled,
                    price=_dec(row.get("ord_unpr")) or None,
                    status=OrderStatus.PARTIALLY_FILLED if filled > 0 else OrderStatus.OPEN,
                    ts=datetime.now(),
                    meta={
                        "krx_fwdg_ord_orgno": row.get("ord_gno_brno", ""),
                        "psbl_qty": str(row.get("psbl_qty", "")),
                    },
                )
            )
        return orders

    # ------------------------------------------------------------------ 주문
    def place_order(self, request: OrderRequest) -> Order:
        # ORD_DVSN: 00 지정가 / 01 시장가
        ord_dvsn = "01" if request.order_type == OrderType.MARKET else "00"
        price = request.price if request.order_type == OrderType.LIMIT else Decimal(0)

        tr_id = "TTTC0012U" if request.side == OrderSide.BUY else "TTTC0011U"
        body = {
            "CANO": self.settings.account,
            "ACNT_PRDT_CD": self.settings.product,
            "PDNO": request.symbol,
            "ORD_DVSN": ord_dvsn,
            "ORD_QTY": str(int(request.quantity)),  # 문자열 필수
            "ORD_UNPR": str(int(price)),
            "EXCG_ID_DVSN_CD": "KRX",
        }
        if request.side == OrderSide.SELL:
            body["SLL_TYPE"] = "01"  # 일반매도
        body["CNDT_PRIC"] = ""

        data = self.client.post("/uapi/domestic-stock/v1/trading/order-cash", tr_id, body)
        output = data["output"]
        return Order(  # noqa: 아래 wait_fill로 체결 확인 가능
            order_id=output["ODNO"],
            symbol=request.symbol,
            side=request.side,
            quantity=request.quantity,
            filled_quantity=Decimal(0),
            price=request.price,
            status=OrderStatus.OPEN,
            ts=datetime.now(),
            meta={
                "krx_fwdg_ord_orgno": output.get("KRX_FWDG_ORD_ORGNO", ""),
                "ord_tmd": output.get("ORD_TMD", ""),
            },
        )

    def get_order_fill(self, odno: str) -> tuple[Decimal, Decimal | None]:
        """당일 주문의 (총체결수량, 평균체결가). 미체결이면 (0, None).

        주식일별주문체결조회(TTTC0081R/VTTC0081R) — ODNO 필터.
        """
        tr_id = "VTTC0081R" if self.settings.is_paper else "TTTC0081R"
        today = date.today().strftime("%Y%m%d")
        data = self.client.get(
            "/uapi/domestic-stock/v1/trading/inquire-daily-ccld", tr_id,
            {
                "CANO": self.settings.account, "ACNT_PRDT_CD": self.settings.product,
                "INQR_STRT_DT": today, "INQR_END_DT": today,
                "SLL_BUY_DVSN_CD": "00", "PDNO": "", "CCLD_DVSN": "00",
                "INQR_DVSN": "00", "INQR_DVSN_1": "", "INQR_DVSN_3": "00",
                "ORD_GNO_BRNO": "", "ODNO": odno,
                "CTX_AREA_FK100": "", "CTX_AREA_NK100": "", "EXCG_ID_DVSN_CD": "KRX",
            },
        )
        key = odno.lstrip("0")
        for row in data.get("output1", []):
            if row.get("odno", "").lstrip("0") == key:
                qty = _dec(row.get("tot_ccld_qty"), "0")
                amt = _dec(row.get("tot_ccld_amt"), "0")
                return qty, (amt / qty if qty > 0 else None)
        return Decimal(0), None

    def cancel_order(self, order: Order) -> None:
        """미체결 주문 전량 취소 (TTTC0013U/VTTC0013U). 이미 체결이면 에러 — 호출부가 무시."""
        tr_id = "VTTC0013U" if self.settings.is_paper else "TTTC0013U"
        self.client.post(
            "/uapi/domestic-stock/v1/trading/order-rvsecncl", tr_id,
            {
                "CANO": self.settings.account, "ACNT_PRDT_CD": self.settings.product,
                "KRX_FWDG_ORD_ORGNO": order.meta.get("krx_fwdg_ord_orgno", ""),
                "ORGN_ODNO": order.order_id, "ORD_DVSN": "01",
                "RVSE_CNCL_DVSN_CD": "02",  # 02: 취소
                "ORD_QTY": "0", "ORD_UNPR": "0", "QTY_ALL_ORD_YN": "Y",
                "EXCG_ID_DVSN_CD": "KRX",
            },
        )

    def settle_order(self, order: Order, timeout: float = 20.0
                     ) -> tuple[Decimal, Decimal | None, None]:
        """주문 확정: 체결 대기 → 미체결이면 취소 → 최종 (수량, 평균가, None) 반환.

        수수료 자리는 항상 None — KIS는 주문 조회에 수수료가 없다 (계좌 단위 정산).
        호출부는 근사치(수수료+거래세 0.21%)를 사용한다. 업비트 settle_order와
        시그니처를 맞춰 봇 코드가 브로커를 가리지 않게 한다.

        취소-체결 경합 대비 취소 후 재조회. 미체결 잔량은 취소되므로
        다음 사이클이 새 주문으로 재시도하면 된다 (수량 잠김 없음).
        """
        filled, avg = self.wait_fill(order.order_id, timeout=timeout)
        if filled > 0 and avg is not None:
            return filled, avg, None
        try:
            self.cancel_order(order)
        except Exception:
            pass  # 이미 체결/취소 — 아래 재조회가 진실
        try:
            filled, avg = self.get_order_fill(order.order_id)
        except Exception:
            pass
        return filled, avg, None

    def wait_fill(self, odno: str, timeout: float = 20.0, interval: float = 2.0
                  ) -> tuple[Decimal, Decimal | None]:
        """체결 확인 폴링 — (체결수량, 평균체결가). 장중 시장가는 보통 1~2회 안에 확정."""
        from time import monotonic, sleep

        deadline = monotonic() + timeout
        qty, avg = Decimal(0), None
        while True:
            try:
                qty, avg = self.get_order_fill(odno)
            except Exception:
                pass
            if qty > 0 or monotonic() > deadline:
                return qty, avg
            sleep(interval)

    def cancel_order(self, order: Order) -> None:
        """전량 취소."""
        self.client.post(
            "/uapi/domestic-stock/v1/trading/order-rvsecncl",
            "TTTC0013U",
            {
                "CANO": self.settings.account,
                "ACNT_PRDT_CD": self.settings.product,
                "KRX_FWDG_ORD_ORGNO": order.meta.get("krx_fwdg_ord_orgno", ""),
                "ORGN_ODNO": order.order_id,
                "ORD_DVSN": "00",
                "RVSE_CNCL_DVSN_CD": "02",  # 01 정정 / 02 취소
                "ORD_QTY": "0",
                "ORD_UNPR": "0",
                "QTY_ALL_ORD_YN": "Y",
                "EXCG_ID_DVSN_CD": "KRX",
            },
        )
