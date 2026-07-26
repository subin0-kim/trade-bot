---
name: kis-api-domestic-bond
scope: shared
updated: 2026-07-26
sources:
  - ../open-trading-api/examples_llm/domestic_bond/ (자동 생성: scripts/gen_kis_api_catalog.py)
---

# KIS API 카탈로그 — 국내채권 (18개)

> 전체 스펙(전 파라미터·응답 필드)은 `../open-trading-api/examples_llm/domestic_bond/<함수명>/` 참조.
> 시그니처의 `[, +N opt]`는 생략 가능한 파라미터 개수. tr_id 첫 글자 T/J/C는 모의투자에서 V로 치환됨 ([[kis-api-notes]]).

## 기본시세

| 함수 원형 | 설명 | tr_id | URL |
|---|---|---|---|
| `avg_unit(inqr_strt_dt, inqr_end_dt, pdno, prdt_type_cd, vrfc_kind_cd[, +8 opt])` | 장내채권 평균단가조회 [국내채권-158] | CTPF2005R | `/uapi/domestic-bond/v1/quotations/avg-unit` |
| `inquire_asking_price(fid_cond_mrkt_div_code, fid_input_iscd[, +4 opt])` | 장내채권현재가(호가) [국내주식-132] | FHKBJ773401C0 | `/uapi/domestic-bond/v1/quotations/inquire-asking-price` |
| `inquire_ccnl(fid_cond_mrkt_div_code, fid_input_iscd[, +4 opt])` | 장내채권현재가(체결) [국내주식-201] | FHKBJ773403C0 | `/uapi/domestic-bond/v1/quotations/inquire-ccnl` |
| `inquire_daily_itemchartprice(fid_cond_mrkt_div_code, fid_input_iscd[, +4 opt])` | 장내채권 기간별시세(일) [국내주식-159] | FHKBJ773701C0 | `/uapi/domestic-bond/v1/quotations/inquire-daily-itemchartprice` |
| `inquire_daily_price(fid_cond_mrkt_div_code, fid_input_iscd[, +4 opt])` | 장내채권현재가(일별) [국내주식-202] | FHKBJ773404C0 | `/uapi/domestic-bond/v1/quotations/inquire-daily-price` |
| `inquire_price(fid_cond_mrkt_div_code, fid_input_iscd[, +4 opt])` | 장내채권현재가(시세) [국내주식-200] | FHKBJ773400C0 | `/uapi/domestic-bond/v1/quotations/inquire-price` |
| `issue_info(pdno, prdt_type_cd[, +4 opt])` | 장내채권 발행정보 [국내주식-156] | CTPF1101R | `/uapi/domestic-bond/v1/quotations/issue-info` |
| `search_bond_info(pdno, prdt_type_cd[, +4 opt])` | 장내채권 기본조회 [국내주식-129] | CTPF1114R | `/uapi/domestic-bond/v1/quotations/search-bond-info` |

## 실시간시세

| 함수 원형 | 설명 | tr_id | URL |
|---|---|---|---|
| `bond_asking_price(tr_type, tr_key)` | 일반채권 실시간호가 [실시간-053] | H0BJASP0 | `(웹소켓)` |
| `bond_ccnl(tr_type, tr_key)` | 일반채권 실시간체결가 [실시간-052] | H0BJCNT0 | `(웹소켓)` |
| `bond_index_ccnl(tr_type, tr_key)` | 채권지수 실시간체결가 [실시간-060] | H0BICNT0 | `(웹소켓)` |

## 주문/계좌

| 함수 원형 | 설명 | tr_id | URL |
|---|---|---|---|
| `buy(cano, acnt_prdt_cd, pdno, ord_qty2, bond_ord_unpr, samt_mket_ptci_yn, bond_rtl_mket_yn[, +4 opt])` | 장내채권 매수주문 [국내주식-124] | TTTC0952U | `/uapi/domestic-bond/v1/trading/buy` |
| `inquire_balance(cano, acnt_prdt_cd, inqr_cndt, pdno, buy_dt[, +6 opt])` | 장내채권 잔고조회 [국내주식-198] | CTSC8407R | `/uapi/domestic-bond/v1/trading/inquire-balance` |
| `inquire_daily_ccld(cano, acnt_prdt_cd, inqr_strt_dt, inqr_end_dt, sll_buy_dvsn_cd, sort_sqn_dvsn, pdno, nccs_yn, ctx_area_nk200, ctx_area_fk200[, +5 opt])` | 장내채권 일별체결조회 [국내주식-127] | CTSC8013R | `/uapi/domestic-bond/v1/trading/inquire-daily-ccld` |
| `inquire_psbl_order(cano, acnt_prdt_cd, pdno, bond_ord_unpr[, +4 opt])` | 장내채권 매수가능조회 [국내주식-199] | TTTC8910R | `/uapi/domestic-bond/v1/trading/inquire-psbl-order` |
| `inquire_psbl_rvsecncl(cano, acnt_prdt_cd, ord_dt, odno, ctx_area_fk200, ctx_area_nk200[, +4 opt])` | 채권정정취소가능주문조회 [국내주식-126] | CTSC8035R | `/uapi/domestic-bond/v1/trading/inquire-psbl-rvsecncl` |
| `order_rvsecncl(cano, acnt_prdt_cd, pdno, orgn_odno, ord_qty2, bond_ord_unpr, qty_all_ord_yn, rvse_cncl_dvsn_cd[, +3 opt])` | 장내채권 정정취소주문 [국내주식-125] | TTTC0953U | `/uapi/domestic-bond/v1/trading/order-rvsecncl` |
| `sell(cano, acnt_prdt_cd, ord_dvsn, pdno, ord_qty2, bond_ord_unpr, sprx_yn, samt_mket_ptci_yn, sll_agco_opps_sll_yn, bond_rtl_mket_yn[, +5 opt])` | 장내채권 매도주문 [국내주식-123] | TTTC0958U | `/uapi/domestic-bond/v1/trading/sell` |
