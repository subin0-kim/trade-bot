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
        return Order(
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
