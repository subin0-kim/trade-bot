---
name: kis-api-domestic-futureoption
scope: shared
updated: 2026-07-26
sources:
  - ../open-trading-api/examples_llm/domestic_futureoption/ (자동 생성: scripts/gen_kis_api_catalog.py)
---

# KIS API 카탈로그 — 국내선물옵션 (43개)

> 전체 스펙(전 파라미터·응답 필드)은 `../open-trading-api/examples_llm/domestic_futureoption/<함수명>/` 참조.
> 시그니처의 `[, +N opt]`는 생략 가능한 파라미터 개수. tr_id 첫 글자 T/J/C는 모의투자에서 V로 치환됨 ([[kis-api-notes]]).

## 기본시세

| 함수 원형 | 설명 | tr_id | URL |
|---|---|---|---|
| `display_board_callput(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_mrkt_cls_code, fid_mtrt_cnt, fid_mrkt_cls_code1[, +1 opt])` | 국내옵션전광판_콜풋[국내선물-022] | FHPIF05030100 | `/uapi/domestic-futureoption/v1/quotations/display-board-callput` |
| `display_board_futures(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_cond_mrkt_cls_code)` | 국내옵션전광판_선물[국내선물-023] | FHPIF05030200 | `/uapi/domestic-futureoption/v1/quotations/display-board-futures` |
| `display_board_option_list(fid_cond_scr_div_code[, +2 opt])` | 국내옵션전광판_옵션월물리스트[국내선물-020] | FHPIO056104C0 | `/uapi/domestic-futureoption/v1/quotations/display-board-option-list` |
| `display_board_top(fid_cond_mrkt_div_code, fid_input_iscd[, +4 opt])` | 국내선물 기초자산 시세[국내선물-021] | FHPIF05030000 | `/uapi/domestic-futureoption/v1/quotations/display-board-top` |
| `exp_price_trend(fid_input_iscd, fid_cond_mrkt_div_code)` | 선물옵션 일중예상체결추이[국내선물-018] | FHPIF05110100 | `/uapi/domestic-futureoption/v1/quotations/exp-price-trend` |
| `inquire_asking_price(fid_cond_mrkt_div_code, fid_input_iscd, env_dv)` | 선물옵션 시세호가[v1_국내선물-007] | FHMIF10010000 | `/uapi/domestic-futureoption/v1/quotations/inquire-asking-price` |
| `inquire_daily_fuopchartprice(fid_cond_mrkt_div_code, fid_input_iscd, fid_input_date_1, fid_input_date_2, fid_period_div_code, env_dv)` | 선물옵션기간별시세(일/주/월/년)[v1_국내선물-008] | FHKIF03020100 | `/uapi/domestic-futureoption/v1/quotations/inquire-daily-fuopchartprice` |
| `inquire_price(fid_cond_mrkt_div_code, fid_input_iscd, env_dv)` | 선물옵션 시세[v1_국내선물-006] | FHMIF10000000 | `/uapi/domestic-futureoption/v1/quotations/inquire-price` |
| `inquire_time_fuopchartprice(fid_cond_mrkt_div_code, fid_input_iscd, fid_hour_cls_code, fid_pw_data_incu_yn, fid_fake_tick_incu_yn, fid_input_date_1, fid_input_hour_1)` | 선물옵션 분봉조회[v1_국내선물-012] | FHKIF03020200 | `/uapi/domestic-futureoption/v1/quotations/inquire-time-fuopchartprice` |

## 실시간시세

| 함수 원형 | 설명 | tr_id | URL |
|---|---|---|---|
| `commodity_futures_realtime_conclusion(tr_type, tr_key)` | 상품선물 실시간체결가[실시간-022] | H0CFCNT0 | `(웹소켓)` |
| `commodity_futures_realtime_quote(tr_type, tr_key)` | 상품선물 실시간호가[실시간-023] | H0CFASP0 | `(웹소켓)` |
| `fuopt_ccnl_notice(tr_type, tr_key)` | 선물옵션 실시간체결통보[실시간-012] | H0IFCNI0 | `(웹소켓)` |
| `futures_exp_ccnl(tr_type, tr_key)` | 주식선물 실시간예상체결 [실시간-031] | H0ZFANC0 | `(웹소켓)` |
| `index_futures_realtime_conclusion(tr_type, tr_key)` | 지수선물 실시간체결가[실시간-010] | H0IFCNT0 | `(웹소켓)` |
| `index_futures_realtime_quote(tr_type, tr_key)` | 지수선물 실시간호가[실시간-011] | H0IFASP0 | `(웹소켓)` |
| `index_option_realtime_conclusion(tr_type, tr_key)` | 지수옵션 실시간체결가[실시간-014] | H0IOCNT0 | `(웹소켓)` |
| `index_option_realtime_quote(tr_type, tr_key)` | 지수옵션 실시간호가[실시간-015] | H0IOASP0 | `(웹소켓)` |
| `krx_ngt_futures_asking_price(tr_type, tr_key)` | KRX야간선물 실시간호가 [실시간-065] | H0MFASP0 | `(웹소켓)` |
| `krx_ngt_futures_ccnl(tr_type, tr_key)` | KRX야간선물 실시간종목체결 [실시간-064] | H0MFCNT0 | `(웹소켓)` |
| `krx_ngt_futures_ccnl_notice(tr_type, tr_key)` | KRX야간선물 실시간체결통보 [실시간-066] | H0MFCNI0 | `(웹소켓)` |
| `krx_ngt_option_asking_price(tr_type, tr_key)` | KRX야간옵션 실시간호가 [실시간-033] | H0EUASP0 | `(웹소켓)` |
| `krx_ngt_option_ccnl(tr_type, tr_key)` | KRX야간옵션 실시간체결가 [실시간-032] | H0EUCNT0 | `(웹소켓)` |
| `krx_ngt_option_exp_ccnl(tr_type, tr_key)` | KRX야간옵션실시간예상체결 [실시간-034] | H0EUANC0 | `(웹소켓)` |
| `krx_ngt_option_notice(tr_type, tr_key)` | KRX야간옵션실시간체결통보 [실시간-067] | H0EUCNI0 | `(웹소켓)` |
| `option_exp_ccnl(tr_type, tr_key)` | 주식옵션 실시간예상체결 [실시간-046] | H0ZOANC0 | `(웹소켓)` |
| `stock_futures_realtime_conclusion(tr_type, tr_key)` | 주식선물 실시간체결가 [실시간-029] | H0ZFCNT0 | `(웹소켓)` |
| `stock_futures_realtime_quote(tr_type, tr_key)` | 주식선물 실시간호가 [실시간-030] | H0ZFASP0 | `(웹소켓)` |
| `stock_option_asking_price(tr_type, tr_key)` | 주식옵션 실시간호가 [실시간-045] | H0ZOASP0 | `(웹소켓)` |
| `stock_option_ccnl(tr_type, tr_key)` | 주식옵션 실시간체결가 [실시간-044] | H0ZOCNT0 | `(웹소켓)` |

## 주문/계좌

| 함수 원형 | 설명 | tr_id | URL |
|---|---|---|---|
| `inquire_balance(env_dv, cano, acnt_prdt_cd, mgna_dvsn, excc_stat_cd[, +7 opt])` | 선물옵션 잔고현황[v1_국내선물-004] | CTFO6118R, VTFO6118R | `/uapi/domestic-futureoption/v1/trading/inquire-balance` |
| `inquire_balance_settlement_pl(cano, acnt_prdt_cd, inqr_dt[, +7 opt])` | 선물옵션 잔고정산손익내역[v1_국내선물-013] | CTFO6117R | `/uapi/domestic-futureoption/v1/trading/inquire-balance-settlement-pl` |
| `inquire_balance_valuation_pl(cano, acnt_prdt_cd, mgna_dvsn, excc_stat_cd[, +7 opt])` | 선물옵션 잔고평가손익내역[v1_국내선물-015] | CTFO6159R | `/uapi/domestic-futureoption/v1/trading/inquire-balance-valuation-pl` |
| `inquire_ccnl(env_dv, cano, acnt_prdt_cd, strt_ord_dt, end_ord_dt, sll_buy_dvsn_cd, ccld_nccs_dvsn, sort_sqn[, +10 opt])` | 선물옵션 주문체결내역조회[v1_국내선물-003] | TTTO5201R, VTTO5201R | `/uapi/domestic-futureoption/v1/trading/inquire-ccnl` |
| `inquire_ccnl_bstime(cano, acnt_prdt_cd, ord_dt, fuop_tr_strt_tmd, fuop_tr_end_tmd[, +7 opt])` | 선물옵션 기준일체결내역[v1_국내선물-016] | CTFO5139R | `/uapi/domestic-futureoption/v1/trading/inquire-ccnl-bstime` |
| `inquire_daily_amount_fee(cano, acnt_prdt_cd, inqr_strt_day, inqr_end_day[, +7 opt])` | 선물옵션기간약정수수료일별[v1_국내선물-017] | CTFO6119R | `/uapi/domestic-futureoption/v1/trading/inquire-daily-amount-fee` |
| `inquire_deposit(cano, acnt_prdt_cd)` | 선물옵션 총자산현황[v1_국내선물-014] | CTRP6550R | `/uapi/domestic-futureoption/v1/trading/inquire-deposit` |
| `inquire_ngt_balance(cano, acnt_prdt_cd, mgna_dvsn, excc_stat_cd[, +8 opt])` | (야간)선물옵션 잔고현황 [국내선물-010] | CTFN6118R | `/uapi/domestic-futureoption/v1/trading/inquire-ngt-balance` |
| `inquire_ngt_ccnl(cano, acnt_prdt_cd, strt_ord_dt, end_ord_dt, sll_buy_dvsn_cd, ccld_nccs_dvsn[, +13 opt])` | (야간)선물옵션 주문체결 내역조회 [국내선물-009] | STTN5201R | `/uapi/domestic-futureoption/v1/trading/inquire-ngt-ccnl` |
| `inquire_psbl_ngt_order(cano, acnt_prdt_cd, pdno, prdt_type_cd, sll_buy_dvsn_cd, unit_price, ord_dvsn_cd)` | (야간)선물옵션 주문가능 조회 [국내선물-011] | STTN5105R | `/uapi/domestic-futureoption/v1/trading/inquire-psbl-ngt-order` |
| `inquire_psbl_order(env_dv, cano, acnt_prdt_cd, pdno, sll_buy_dvsn_cd, unit_price, ord_dvsn_cd)` | 선물옵션 주문가능[v1_국내선물-005] | TTTO5105R, VTTO5105R | `/uapi/domestic-futureoption/v1/trading/inquire-psbl-order` |
| `ngt_margin_detail(cano, acnt_prdt_cd, mgna_dvsn_cd)` | (야간)선물옵션 증거금 상세 [국내선물-024] | CTFN7107R | `/uapi/domestic-futureoption/v1/trading/ngt-margin-detail` |
| `order(env_dv, ord_dv, ord_prcs_dvsn_cd, cano, acnt_prdt_cd, sll_buy_dvsn_cd, shtn_pdno, ord_qty, unit_price, nmpr_type_cd, krx_nmpr_cndt_cd, ord_dvsn_cd[, +2 opt])` | 선물옵션 주문[v1_국내선물-001] | STTN1101U, TTTO1101U, VTTO1101U | `/uapi/domestic-futureoption/v1/trading/order` |
| `order_rvsecncl(env_dv, day_dv, ord_prcs_dvsn_cd, cano, acnt_prdt_cd, rvse_cncl_dvsn_cd, orgn_odno, ord_qty, unit_price, nmpr_type_cd, krx_nmpr_cndt_cd, rmn_qty_yn, ord_dvsn_cd[, +1 opt])` | 선물옵션 정정취소주문[v1_국내선물-002] | TTTN1103U, TTTO1103U, VTTO1103U | `/uapi/domestic-futureoption/v1/trading/order-rvsecncl` |
