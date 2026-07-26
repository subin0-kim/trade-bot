---
name: kis-api-overseas-futureoption
scope: shared
updated: 2026-07-26
sources:
  - ../open-trading-api/examples_llm/overseas_futureoption/ (자동 생성: scripts/gen_kis_api_catalog.py)
---

# KIS API 카탈로그 — 해외선물옵션 (35개)

> 전체 스펙(전 파라미터·응답 필드)은 `../open-trading-api/examples_llm/overseas_futureoption/<함수명>/` 참조.
> 시그니처의 `[, +N opt]`는 생략 가능한 파라미터 개수. tr_id 첫 글자 T/J/C는 모의투자에서 V로 치환됨 ([[kis-api-notes]]).

## 기본시세

| 함수 원형 | 설명 | tr_id | URL |
|---|---|---|---|
| `daily_ccnl(srs_cd, exch_cd, start_date_time, close_date_time, qry_tp, qry_cnt, qry_gap, index_key[, +5 opt])` | 해외선물 체결추이(일간) [해외선물-018] | HHDFC55020100 | `/uapi/overseas-futureoption/v1/quotations/daily-ccnl` |
| `inquire_asking_price(srs_cd[, +5 opt])` | 해외선물 호가 [해외선물-031] | HHDFC86000000 | `/uapi/overseas-futureoption/v1/quotations/inquire-asking-price` |
| `inquire_price(srs_cd[, +4 opt])` | 해외선물종목현재가 [v1_해외선물-009] | HHDFC55010000 | `/uapi/overseas-futureoption/v1/quotations/inquire-price` |
| `inquire_time_futurechartprice(srs_cd, exch_cd, start_date_time, close_date_time, qry_tp, qry_cnt, qry_gap, index_key[, +5 opt])` | 해외선물 분봉조회[해외선물-016] | HHDFC55020400 | `/uapi/overseas-futureoption/v1/quotations/inquire-time-futurechartprice` |
| `inquire_time_optchartprice(srs_cd, exch_cd, qry_cnt[, +10 opt])` | 해외옵션 분봉조회 [해외선물-040] | HHDFO55020100 | `/uapi/overseas-futureoption/v1/quotations/inquire-time-optchartprice` |
| `investor_unpd_trend(prod_iscd, bsop_date, upmu_gubun, cts_key[, +5 opt])` | 해외선물 미결제추이 [해외선물-029] | HHDDB95030000 | `/uapi/overseas-futureoption/v1/quotations/investor-unpd-trend` |
| `market_time(fm_pdgr_cd, fm_clas_cd, fm_excg_cd, opt_yn, ctx_area_nk200, ctx_area_fk200[, +4 opt])` | 해외선물옵션 장운영시간 [해외선물-030] | OTFM2229R | `/uapi/overseas-futureoption/v1/quotations/market-time` |
| `monthly_ccnl(srs_cd, exch_cd, start_date_time, close_date_time, qry_tp, qry_cnt, qry_gap, index_key[, +5 opt])` | 해외선물 체결추이(월간)[해외선물-020] | HHDFC55020300 | `/uapi/overseas-futureoption/v1/quotations/monthly-ccnl` |
| `opt_asking_price(srs_cd[, +5 opt])` | 해외옵션 호가 [해외선물-033] | HHDFO86000000 | `/uapi/overseas-futureoption/v1/quotations/opt-asking-price` |
| `opt_daily_ccnl(srs_cd, exch_cd, qry_cnt[, +10 opt])` | 해외옵션 체결추이(일간) [해외선물-037] | HHDFO55020100 | `/uapi/overseas-futureoption/v1/quotations/opt-daily-ccnl` |
| `opt_detail(srs_cd)` | 해외옵션종목상세 [해외선물-034] | HHDFO55010100 | `/uapi/overseas-futureoption/v1/quotations/opt-detail` |
| `opt_monthly_ccnl(srs_cd, exch_cd, qry_cnt[, +10 opt])` | 해외옵션 체결추이(월간) [해외선물-039] | HHDFO55020300 | `/uapi/overseas-futureoption/v1/quotations/opt-monthly-ccnl` |
| `opt_price(srs_cd)` | 해외옵션종목현재가 [해외선물-035] | HHDFO55010000 | `/uapi/overseas-futureoption/v1/quotations/opt-price` |
| `opt_tick_ccnl(srs_cd, exch_cd, qry_cnt[, +10 opt])` | 해외옵션 체결추이(틱) [해외선물-038] | HHDFO55020200 | `/uapi/overseas-futureoption/v1/quotations/opt-tick-ccnl` |
| `opt_weekly_ccnl(srs_cd, exch_cd, qry_cnt[, +10 opt])` | 해외옵션 체결추이(주간) [해외선물-036] | HHDFO55020000 | `/uapi/overseas-futureoption/v1/quotations/opt-weekly-ccnl` |
| `search_contract_detail(qry_cnt[, +4 opt])` | 해외선물 상품기본정보[해외선물-023] | HHDFC55200000 | `/uapi/overseas-futureoption/v1/quotations/search-contract-detail` |
| `search_opt_detail(qry_cnt, srs_cd_01[, +29 opt])` | 해외옵션 상품기본정보 [해외선물-041] | HHDFO55200000 | `/uapi/overseas-futureoption/v1/quotations/search-opt-detail` |
| `stock_detail(srs_cd[, +4 opt])` | 해외선물종목상세[v1_해외선물-008] | HHDFC55010100 | `/uapi/overseas-futureoption/v1/quotations/stock-detail` |
| `tick_ccnl(srs_cd, exch_cd, start_date_time, close_date_time, qry_tp, qry_cnt, qry_gap, index_key[, +5 opt])` | 해외선물 체결추이(틱)[해외선물-019] | HHDFC55020200 | `/uapi/overseas-futureoption/v1/quotations/tick-ccnl` |
| `weekly_ccnl(srs_cd, exch_cd, start_date_time, close_date_time, qry_tp, qry_cnt, qry_gap, index_key[, +5 opt])` | 해외선물 체결추이(주간)[해외선물-017] | HHDFC55020000 | `/uapi/overseas-futureoption/v1/quotations/weekly-ccnl` |

## 실시간시세

| 함수 원형 | 설명 | tr_id | URL |
|---|---|---|---|
| `asking_price(tr_type, tr_key)` | 해외선물옵션 실시간호가[실시간-018] | HDFFF010 | `(웹소켓)` |
| `ccnl(tr_type, tr_key)` | 해외선물옵션 실시간체결가[실시간-017] | HDFFF020 | `(웹소켓)` |
| `ccnl_notice(tr_type, tr_key)` | 해외선물옵션 실시간체결내역통보[실시간-020] | HDFFF2C0 | `(웹소켓)` |
| `order_notice(tr_type, tr_key)` | 해외선물옵션 실시간주문내역통보[실시간-019] | HDFFF1C0 | `(웹소켓)` |

## 주문/계좌

| 함수 원형 | 설명 | tr_id | URL |
|---|---|---|---|
| `inquire_ccld(cano, acnt_prdt_cd, ccld_nccs_dvsn, sll_buy_dvsn_cd, fuop_dvsn, ctx_area_fk200, ctx_area_nk200[, +4 opt])` | 해외선물옵션 당일주문내역조회 [v1_해외선물-004] | OTFM3116R | `/uapi/overseas-futureoption/v1/trading/inquire-ccld` |
| `inquire_daily_ccld(cano, acnt_prdt_cd, strt_dt, end_dt, fuop_dvsn_cd, fm_pdgr_cd, crcy_cd, fm_item_ftng_yn, sll_buy_dvsn_cd, ctx_area_fk200, ctx_area_nk200[, +5 opt])` | 해외선물옵션 일별체결내역[해외선물-011] | OTFM3122R | `/uapi/overseas-futureoption/v1/trading/inquire-daily-ccld` |
| `inquire_daily_order(cano, acnt_prdt_cd, strt_dt, end_dt, fm_pdgr_cd, ccld_nccs_dvsn, sll_buy_dvsn_cd, fuop_dvsn, ctx_area_fk200, ctx_area_nk200[, +4 opt])` | 해외선물옵션 일별 주문내역 [해외선물-013] | OTFM3120R | `/uapi/overseas-futureoption/v1/trading/inquire-daily-order` |
| `inquire_deposit(cano, acnt_prdt_cd, crcy_cd, inqr_dt[, +4 opt])` | 해외선물옵션 예수금현황 [해외선물-012] | OTFM1411R | `/uapi/overseas-futureoption/v1/trading/inquire-deposit` |
| `inquire_period_ccld(inqr_term_from_dt, inqr_term_to_dt, cano, acnt_prdt_cd, crcy_cd, whol_trsl_yn, fuop_dvsn, ctx_area_fk200, ctx_area_nk200[, +5 opt])` | 해외선물옵션 기간계좌손익 일별 [해외선물-010] | OTFM3118R | `/uapi/overseas-futureoption/v1/trading/inquire-period-ccld` |
| `inquire_period_trans(inqr_term_from_dt, inqr_term_to_dt, cano, acnt_prdt_cd, acnt_tr_type_cd, crcy_cd, ctx_area_fk100, ctx_area_nk100, pwd_chk_yn[, +4 opt])` | 해외선물옵션 기간계좌거래내역 [해외선물-014] | OTFM3114R | `/uapi/overseas-futureoption/v1/trading/inquire-period-trans` |
| `inquire_psamount(cano, acnt_prdt_cd, ovrs_futr_fx_pdno, sll_buy_dvsn_cd, fm_ord_pric, ecis_rsvn_ord_yn[, +4 opt])` | 해외선물옵션 주문가능조회 [v1_해외선물-006] | OTFM3304R | `/uapi/overseas-futureoption/v1/trading/inquire-psamount` |
| `inquire_unpd(cano, acnt_prdt_cd, fuop_dvsn, ctx_area_fk100, ctx_area_nk100[, +4 opt])` | 해외선물옵션 미결제내역조회(잔고) [v1_해외선물-005] | OTFM1412R | `/uapi/overseas-futureoption/v1/trading/inquire-unpd` |
| `margin_detail(cano, acnt_prdt_cd, crcy_cd, inqr_dt[, +4 opt])` | 해외선물옵션 증거금상세 [해외선물-032] | OTFM3115R | `/uapi/overseas-futureoption/v1/trading/margin-detail` |
| `order(cano, acnt_prdt_cd, ovrs_futr_fx_pdno, sll_buy_dvsn_cd, fm_lqd_ustl_ccld_dt, fm_lqd_ustl_ccno, pric_dvsn_cd, fm_limit_ord_pric, fm_stop_ord_pric, fm_ord_qty, fm_lqd_lmt_ord_pric, fm_lqd_stop_ord_pric, ccld_cndt_cd, cplx_ord_dvsn_cd, ecis_rsvn_ord_yn, fm_hdge_ord_scrn_yn)` | 해외선물옵션 주문[v1_해외선물-001] | OTFM3001U | `/uapi/overseas-futureoption/v1/trading/order` |
| `order_rvsecncl(cano, ord_dv, acnt_prdt_cd, orgn_ord_dt, orgn_odno, fm_limit_ord_pric, fm_stop_ord_pric, fm_lqd_lmt_ord_pric, fm_lqd_stop_ord_pric, fm_hdge_ord_scrn_yn, fm_mkpr_cvsn_yn)` | 해외선물옵션 정정취소주문[v1_해외선물-002, 003] | OTFM3002U, OTFM3003U | `/uapi/overseas-futureoption/v1/trading/order-rvsecncl` |
