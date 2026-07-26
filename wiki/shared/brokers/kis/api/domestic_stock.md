---
name: kis-api-domestic-stock
scope: shared
updated: 2026-07-26
sources:
  - ../open-trading-api/examples_llm/domestic_stock/ (자동 생성: scripts/gen_kis_api_catalog.py)
---

# KIS API 카탈로그 — 국내주식 (156개)

> 전체 스펙(전 파라미터·응답 필드)은 `../open-trading-api/examples_llm/domestic_stock/<함수명>/` 참조.
> 시그니처의 `[, +N opt]`는 생략 가능한 파라미터 개수. tr_id 첫 글자 T/J/C는 모의투자에서 V로 치환됨 ([[kis-api-notes]]).

## ELW시세

| 함수 원형 | 설명 | tr_id | URL |
|---|---|---|---|
| `inquire_elw_price(fid_cond_mrkt_div_code, fid_input_iscd[, +5 opt])` | ELW 현재가 시세 [v1_국내주식-014] | FHKEW15010000 | `/uapi/domestic-stock/v1/quotations/inquire-elw-price` |

## 국내주식

| 함수 원형 | 설명 | tr_id | URL |
|---|---|---|---|
| `overtime_volume(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_rank_sort_cls_code, fid_input_price_1, fid_input_price_2, fid_vol_cnt, fid_trgt_cls_code, fid_trgt_exls_cls_code[, +5 opt])` | 국내주식 시간외거래량순위[국내주식-139] | FHPST02350000 | `/uapi/domestic-stock/v1/ranking/overtime-volume` |

## 기본시세

| 함수 원형 | 설명 | tr_id | URL |
|---|---|---|---|
| `after_hour_balance(fid_input_price_1, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_rank_sort_cls_code, fid_div_cls_code, fid_input_iscd, fid_trgt_exls_cls_code, fid_trgt_cls_code, fid_vol_cnt, fid_input_price_2[, +4 opt])` | 국내주식 시간외잔량 순위[v1_국내주식-093] | FHPST01760000 | `/uapi/domestic-stock/v1/ranking/after-hour-balance` |
| `exp_closing_price(fid_cond_mrkt_div_code, fid_input_iscd, fid_rank_sort_cls_code, fid_cond_scr_div_code, fid_blng_cls_code)` | 국내주식 장마감 예상체결가[국내주식-120] | FHKST117300C0 | `/uapi/domestic-stock/v1/quotations/exp-closing-price` |
| `frgnmem_trade_trend(fid_cond_scr_div_code, fid_cond_mrkt_div_code, fid_input_iscd, fid_input_iscd_2, fid_mrkt_cls_code, fid_vol_cnt[, +5 opt])` | 회원사 실 시간 매매동향(틱)[국내주식-163] | FHPST04320000 | `/uapi/domestic-stock/v1/quotations/frgnmem-trade-trend` |
| `inquire_asking_price_exp_ccn(env_dv, fid_cond_mrkt_div_code, fid_input_iscd)` | 주식현재가 호가/예상체결[v1_국내주식-011] | FHKST01010200 | `/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn` |
| `inquire_ccnl(env_dv, fid_cond_mrkt_div_code, fid_input_iscd)` | 주식현재가 체결[v1_국내주식-009] | FHKST01010300 | `/uapi/domestic-stock/v1/quotations/inquire-ccnl` |
| `inquire_daily_indexchartprice(fid_cond_mrkt_div_code, fid_input_iscd, fid_input_date_1, fid_input_date_2, fid_period_div_code[, +6 opt])` | 국내주식업종기간별시세(일_주_월_년)[v1_국내주식-021] | FHKUP03500100 | `/uapi/domestic-stock/v1/quotations/inquire-daily-indexchartprice` |
| `inquire_daily_itemchartprice(env_dv, fid_cond_mrkt_div_code, fid_input_iscd, fid_input_date_1, fid_input_date_2, fid_period_div_code, fid_org_adj_prc)` | 국내주식기간별시세(일/주/월/년)[v1_국내주식-016] | FHKST03010100 | `/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice` |
| `inquire_daily_overtimeprice(env_dv, fid_cond_mrkt_div_code, fid_input_iscd)` | 주식현재가 시간외일자별주가[v1_국내주식-026] | FHPST02320000 | `/uapi/domestic-stock/v1/quotations/inquire-daily-overtimeprice` |
| `inquire_daily_price(env_dv, fid_cond_mrkt_div_code, fid_input_iscd, fid_period_div_code, fid_org_adj_prc)` | 주식현재가 일자별[v1_국내주식-010] | FHKST01010400 | `/uapi/domestic-stock/v1/quotations/inquire-daily-price` |
| `inquire_investor(env_dv, fid_cond_mrkt_div_code, fid_input_iscd)` | 주식현재가 투자자[v1_국내주식-012] | FHKST01010900 | `/uapi/domestic-stock/v1/quotations/inquire-investor` |
| `inquire_member(env_dv, fid_cond_mrkt_div_code, fid_input_iscd)` | 주식현재가 회원사[v1_국내주식-013] | FHKST01010600 | `/uapi/domestic-stock/v1/quotations/inquire-member` |
| `inquire_overtime_asking_price(fid_cond_mrkt_div_code, fid_input_iscd)` | 국내주식 시간외호가[국내주식-077] | FHPST02300400 | `/uapi/domestic-stock/v1/quotations/inquire-overtime-asking-price` |
| `inquire_overtime_price(fid_cond_mrkt_div_code, fid_input_iscd)` | 국내주식 시간외현재가[국내주식-076] | FHPST02300000 | `/uapi/domestic-stock/v1/quotations/inquire-overtime-price` |
| `inquire_price(env_dv, fid_cond_mrkt_div_code, fid_input_iscd)` | 주식현재가 시세[v1_국내주식-008] | FHKST01010100 | `/uapi/domestic-stock/v1/quotations/inquire-price` |
| `inquire_price_2(fid_cond_mrkt_div_code, fid_input_iscd)` | 주식현재가 시세2[v1_국내주식-054] | FHPST01010000 | `/uapi/domestic-stock/v1/quotations/inquire-price-2` |
| `inquire_time_dailychartprice(fid_cond_mrkt_div_code, fid_input_iscd, fid_input_hour_1, fid_input_date_1[, +2 opt])` | 주식일별분봉조회 [국내주식-213] | FHKST03010230 | `/uapi/domestic-stock/v1/quotations/inquire-time-dailychartprice` |
| `inquire_time_indexchartprice(fid_cond_mrkt_div_code, fid_etc_cls_code, fid_input_iscd, fid_input_hour_1, fid_pw_data_incu_yn[, +5 opt])` | 업종 분봉조회[v1_국내주식-045] | FHKUP03500200 | `/uapi/domestic-stock/v1/quotations/inquire-time-indexchartprice` |
| `inquire_time_itemchartprice(env_dv, fid_cond_mrkt_div_code, fid_input_iscd, fid_input_hour_1, fid_pw_data_incu_yn[, +1 opt])` | 주식당일분봉조회[v1_국내주식-022] | FHKST03010200 | `/uapi/domestic-stock/v1/quotations/inquire-time-itemchartprice` |
| `inquire_time_itemconclusion(env_dv, fid_cond_mrkt_div_code, fid_input_iscd, fid_input_hour_1)` | 주식현재가 당일시간대별체결[v1_국내주식-023] | FHPST01060000 | `/uapi/domestic-stock/v1/quotations/inquire-time-itemconclusion` |
| `inquire_time_overtimeconclusion(env_dv, fid_cond_mrkt_div_code, fid_input_iscd, fid_hour_cls_code)` | 주식현재가 시간외시간별체결[v1_국내주식-025] | FHPST02310000 | `/uapi/domestic-stock/v1/quotations/inquire-time-overtimeconclusion` |
| `inquire_vi_status(fid_div_cls_code, fid_cond_scr_div_code, fid_mrkt_cls_code, fid_input_iscd, fid_rank_sort_cls_code, fid_input_date_1, fid_trgt_cls_code, fid_trgt_exls_cls_code[, +4 opt])` | 변동성완화장치(VI) 현황[v1_국내주식-055] | FHPST01390000 | `/uapi/domestic-stock/v1/quotations/inquire-vi-status` |
| `quote_balance(fid_vol_cnt, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_rank_sort_cls_code, fid_div_cls_code, fid_trgt_cls_code, fid_trgt_exls_cls_code, fid_input_price_1, fid_input_price_2[, +2 opt])` | 국내주식 호가잔량 순위[국내주식-089] | FHPST01720000 | `/uapi/domestic-stock/v1/ranking/quote-balance` |

## 순위분석

| 함수 원형 | 설명 | tr_id | URL |
|---|---|---|---|
| `bulk_trans_num(fid_aply_rang_prc_2, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_rank_sort_cls_code, fid_div_cls_code, fid_input_price_1, fid_aply_rang_prc_1, fid_input_iscd_2, fid_trgt_exls_cls_code, fid_trgt_cls_code, fid_vol_cnt[, +4 opt])` | 국내주식 대량체결건수 상위[국내주식-107] | FHKST190900C0 | `/uapi/domestic-stock/v1/ranking/bulk-trans-num` |
| `credit_balance(fid_cond_scr_div_code, fid_input_iscd, fid_option, fid_cond_mrkt_div_code, fid_rank_sort_cls_code[, +5 opt])` | 국내주식 신용잔고 상위 [국내주식-109] | FHKST17010000 | `/uapi/domestic-stock/v1/ranking/credit-balance` |
| `disparity(fid_input_price_2, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_div_cls_code, fid_rank_sort_cls_code, fid_hour_cls_code, fid_input_iscd, fid_trgt_cls_code, fid_trgt_exls_cls_code, fid_input_price_1, fid_vol_cnt[, +4 opt])` | 국내주식 이격도 순위 [v1_국내주식-095] | FHPST01780000 | `/uapi/domestic-stock/v1/ranking/disparity` |
| `dividend_rate(cts_area, gb1, upjong, gb2, gb3, f_dt, t_dt, gb4[, +4 opt])` | 국내주식 배당률 상위[국내주식-106] | HHKDB13470100 | `/uapi/domestic-stock/v1/ranking/dividend-rate` |
| `exp_trans_updown(fid_rank_sort_cls_code, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_div_cls_code, fid_aply_rang_prc_1, fid_vol_cnt, fid_pbmn, fid_blng_cls_code, fid_mkop_cls_code[, +4 opt])` | 국내주식 예상체결 상승_하락상위[v1_국내주식-103] | FHPST01820000 | `/uapi/domestic-stock/v1/ranking/exp-trans-updown` |
| `finance_ratio(fid_trgt_cls_code, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_div_cls_code, fid_input_price_1, fid_input_price_2, fid_vol_cnt, fid_input_option_1, fid_input_option_2, fid_rank_sort_cls_code, fid_blng_cls_code, fid_trgt_exls_cls_code[, +2 opt])` | 국내주식 재무비율 순위[v1_국내주식-092] | FHPST01750000 | `/uapi/domestic-stock/v1/ranking/finance-ratio` |
| `fluctuation(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_rank_sort_cls_code, fid_input_cnt_1, fid_prc_cls_code, fid_input_price_1, fid_input_price_2, fid_vol_cnt, fid_trgt_cls_code, fid_trgt_exls_cls_code, fid_div_cls_code, fid_rsfl_rate1, fid_rsfl_rate2[, +2 opt])` | 등락률 순위[v1_국내주식-088] | FHPST01700000 | `/uapi/domestic-stock/v1/ranking/fluctuation` |
| `hts_top_view([, +4 opt])` | HTS조회상위20종목[국내주식-214] | HHMCM000100C0 | `/uapi/domestic-stock/v1/ranking/hts-top-view` |
| `market_cap(fid_input_price_2, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_div_cls_code, fid_input_iscd, fid_trgt_cls_code, fid_trgt_exls_cls_code, fid_input_price_1, fid_vol_cnt[, +2 opt])` | 국내주식 시가총액 상위 [v1_국내주식-091] | FHPST01740000 | `/uapi/domestic-stock/v1/ranking/market-cap` |
| `market_value(fid_trgt_cls_code, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_div_cls_code, fid_input_price_1, fid_input_price_2, fid_vol_cnt, fid_input_option_1, fid_input_option_2, fid_rank_sort_cls_code, fid_blng_cls_code, fid_trgt_exls_cls_code[, +2 opt])` | 국내주식 시장가치 순위[v1_국내주식-096] | FHPST01790000 | `/uapi/domestic-stock/v1/ranking/market-value` |
| `near_new_highlow(fid_aply_rang_vol, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_div_cls_code, fid_input_cnt_1, fid_input_cnt_2, fid_prc_cls_code, fid_input_iscd, fid_trgt_cls_code, fid_trgt_exls_cls_code, fid_aply_rang_prc_1, fid_aply_rang_prc_2[, +2 opt])` | 국내주식 신고_신저근접종목 상위[v1_국내주식-105] | FHPST01870000 | `/uapi/domestic-stock/v1/ranking/near-new-highlow` |
| `overtime_fluctuation(fid_cond_mrkt_div_code, fid_mrkt_cls_code, fid_cond_scr_div_code, fid_input_iscd, fid_div_cls_code, fid_input_price_1, fid_input_price_2, fid_vol_cnt, fid_trgt_cls_code, fid_trgt_exls_cls_code[, +5 opt])` | 국내주식 시간외등락율순위[국내주식-138] | FHPST02340000 | `/uapi/domestic-stock/v1/ranking/overtime-fluctuation` |
| `prefer_disparate_ratio(fid_vol_cnt, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_div_cls_code, fid_input_iscd, fid_trgt_cls_code, fid_trgt_exls_cls_code, fid_input_price_1, fid_input_price_2[, +4 opt])` | 국내주식 우선주_괴리율 상위[v1_국내주식-094] | FHPST01770000 | `/uapi/domestic-stock/v1/ranking/prefer-disparate-ratio` |
| `profit_asset_index(fid_cond_mrkt_div_code, fid_trgt_cls_code, fid_cond_scr_div_code, fid_input_iscd, fid_div_cls_code, fid_input_price_1, fid_input_price_2, fid_vol_cnt, fid_input_option_1, fid_input_option_2, fid_rank_sort_cls_code, fid_blng_cls_code, fid_trgt_exls_cls_code[, +2 opt])` | 국내주식 수익자산지표 순위[v1_국내주식-090] | FHPST01730000 | `/uapi/domestic-stock/v1/ranking/profit-asset-index` |
| `short_sale(fid_aply_rang_vol, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_period_div_code, fid_input_cnt_1, fid_trgt_exls_cls_code, fid_trgt_cls_code, fid_aply_rang_prc_1, fid_aply_rang_prc_2[, +4 opt])` | 국내주식 공매도 상위종목[국내주식-133] | FHPST04820000 | `/uapi/domestic-stock/v1/ranking/short-sale` |
| `top_interest_stock(fid_input_iscd_2, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_trgt_cls_code, fid_trgt_exls_cls_code, fid_input_price_1, fid_input_price_2, fid_vol_cnt, fid_div_cls_code, fid_input_cnt_1[, +4 opt])` | 국내주식 관심종목등록 상위[v1_국내주식-102] | FHPST01800000 | `/uapi/domestic-stock/v1/ranking/top-interest-stock` |
| `traded_by_company(fid_trgt_exls_cls_code, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_div_cls_code, fid_rank_sort_cls_code, fid_input_date_1, fid_input_date_2, fid_input_iscd, fid_trgt_cls_code, fid_aply_rang_vol, fid_aply_rang_prc_2, fid_aply_rang_prc_1[, +4 opt])` | 국내주식 당사매매종목 상위[v1_국내주식-104] | FHPST01860000 | `/uapi/domestic-stock/v1/ranking/traded-by-company` |
| `volume_power(fid_trgt_exls_cls_code, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_div_cls_code, fid_input_price_1, fid_input_price_2, fid_vol_cnt, fid_trgt_cls_code[, +4 opt])` | 국내주식 체결강도 상위[v1_국내주식-101] | FHPST01680000 | `/uapi/domestic-stock/v1/ranking/volume-power` |
| `volume_rank(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_div_cls_code, fid_blng_cls_code, fid_trgt_cls_code, fid_trgt_exls_cls_code, fid_input_price_1, fid_input_price_2, fid_vol_cnt, fid_input_date_1[, +2 opt])` | 거래량순위[v1_국내주식-047] | FHPST01710000 | `/uapi/domestic-stock/v1/quotations/volume-rank` |

## 시세분석

| 함수 원형 | 설명 | tr_id | URL |
|---|---|---|---|
| `capture_uplowprice(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_prc_cls_code, fid_div_cls_code, fid_input_iscd[, +5 opt])` | 국내주식 상하한가 포착 [국내주식-190] | FHKST130000C0 | `/uapi/domestic-stock/v1/quotations/capture-uplowprice` |
| `comp_program_trade_daily(fid_cond_mrkt_div_code, fid_mrkt_cls_code[, +2 opt])` | 프로그램매매 종합현황(일별)[국내주식-115] | FHPPG04600001 | `/uapi/domestic-stock/v1/quotations/comp-program-trade-daily` |
| `comp_program_trade_today(fid_cond_mrkt_div_code, fid_mrkt_cls_code[, +4 opt])` | 프로그램매매 종합현황(시간) [국내주식-114] | FHPPG04600101 | `/uapi/domestic-stock/v1/quotations/comp-program-trade-today` |
| `daily_credit_balance(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_input_date_1[, +4 opt])` | 국내주식 신용잔고 일별추이[국내주식-110] | FHPST04760000 | `/uapi/domestic-stock/v1/quotations/daily-credit-balance` |
| `daily_loan_trans(mrkt_div_cls_code, mksc_shrn_iscd[, +3 opt])` | 종목별 일별 대차거래추이 [국내주식-135] | HHPST074500C0 | `/uapi/domestic-stock/v1/quotations/daily-loan-trans` |
| `daily_short_sale(fid_cond_mrkt_div_code, fid_input_iscd[, +2 opt])` | 국내주식 공매도 일별추이[국내주식-134] | FHPST04830000 | `/uapi/domestic-stock/v1/quotations/daily-short-sale` |
| `exp_price_trend(fid_cond_mrkt_div_code, fid_input_iscd, fid_mkop_cls_code)` | 국내주식 예상체결가 추이[국내주식-118] | FHPST01810000 | `/uapi/domestic-stock/v1/quotations/exp-price-trend` |
| `foreign_institution_total(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_div_cls_code, fid_rank_sort_cls_code, fid_etc_cls_code)` | 국내기관_외국인 매매종목가집계[국내주식-037] | FHPTJ04400000 | `/uapi/domestic-stock/v1/quotations/foreign-institution-total` |
| `frgnmem_pchs_trend(fid_cond_mrkt_div_code, fid_input_iscd, fid_input_iscd_2)` | 종목별 외국계 순매수추이 [국내주식-164] | FHKST644400C0 | `/uapi/domestic-stock/v1/quotations/frgnmem-pchs-trend` |
| `frgnmem_trade_estimate(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_rank_sort_cls_code, fid_rank_sort_cls_code_2)` | 외국계 매매종목 가집계 [국내주식-161] | FHKST644100C0 | `/uapi/domestic-stock/v1/quotations/frgnmem-trade-estimate` |
| `inquire_daily_trade_volume(fid_cond_mrkt_div_code, fid_input_iscd, fid_period_div_code[, +2 opt])` | 종목별일별매수매도체결량 [v1_국내주식-056] | FHKST03010800 | `/uapi/domestic-stock/v1/quotations/inquire-daily-trade-volume` |
| `inquire_investor_daily_by_market(fid_cond_mrkt_div_code, fid_input_iscd, fid_input_date_1, fid_input_iscd_1, fid_input_date_2, fid_input_iscd_2)` | 시장별 투자자매매동향(일별) [국내주식-075] | FHPTJ04040000 | `/uapi/domestic-stock/v1/quotations/inquire-investor-daily-by-market` |
| `inquire_investor_time_by_market(fid_input_iscd, fid_input_iscd_2)` | 시장별 투자자매매동향(시세)[v1_국내주식-074] | FHPTJ04030000 | `/uapi/domestic-stock/v1/quotations/inquire-investor-time-by-market` |
| `inquire_member_daily(fid_cond_mrkt_div_code, fid_input_iscd, fid_input_iscd_2, fid_input_date_1, fid_input_date_2[, +1 opt])` | 주식현재가 회원사 종목매매동향 [국내주식-197] | FHPST04540000 | `/uapi/domestic-stock/v1/quotations/inquire-member-daily` |
| `intstock_grouplist(type, fid_etc_cls_code, user_id)` | 관심종목 그룹조회 [국내주식-204] | HHKCM113004C7 | `/uapi/domestic-stock/v1/quotations/intstock-grouplist` |
| `intstock_multprice(fid_cond_mrkt_div_code_1, fid_input_iscd_1[, +58 opt])` | 관심종목(멀티종목) 시세조회 [국내주식-205] | FHKST11300006 | `/uapi/domestic-stock/v1/quotations/intstock-multprice` |
| `intstock_stocklist_by_group(type, user_id, inter_grp_code, fid_etc_cls_code[, +4 opt])` | 관심종목 그룹별 종목조회 [국내주식-203] | HHKCM113004C6 | `/uapi/domestic-stock/v1/quotations/intstock-stocklist-by-group` |
| `investor_program_trade_today(mrkt_div_cls_code)` | 프로그램매매 투자자매매동향(당일) [국내주식-116] | HHPPG046600C1 | `/uapi/domestic-stock/v1/quotations/investor-program-trade-today` |
| `investor_trade_by_stock_daily(fid_cond_mrkt_div_code, fid_input_iscd, fid_input_date_1, fid_org_adj_prc, fid_etc_cls_code[, +5 opt])` | 종목별 투자자매매동향(일별)[종목별 투자자매매동향(일별)] | FHPTJ04160001 | `/uapi/domestic-stock/v1/quotations/investor-trade-by-stock-daily` |
| `investor_trend_estimate(mksc_shrn_iscd)` | 종목별 외인기관 추정가집계[v1_국내주식-046] | HHPTJ04160200 | `/uapi/domestic-stock/v1/quotations/investor-trend-estimate` |
| `mktfunds([, +1 opt])` | 국내 증시자금 종합 [국내주식-193] | FHKST649100C0 | `/uapi/domestic-stock/v1/quotations/mktfunds` |
| `overtime_exp_trans_fluct(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_rank_sort_cls_code, fid_div_cls_code[, +3 opt])` | 국내주식 시간외예상체결등락률 [국내주식-140] | FHKST11860000 | `/uapi/domestic-stock/v1/ranking/overtime-exp-trans-fluct` |
| `pbar_tratio(fid_cond_mrkt_div_code, fid_input_iscd, fid_cond_scr_div_code[, +1 opt])` | 국내주식 매물대/거래비중 [국내주식-196] | FHPST01130000 | `/uapi/domestic-stock/v1/quotations/pbar-tratio` |
| `program_trade_by_stock(fid_cond_mrkt_div_code, fid_input_iscd)` | 종목별 프로그램매매추이(체결)[v1_국내주식-044] | FHPPG04650101 | `/uapi/domestic-stock/v1/quotations/program-trade-by-stock` |
| `program_trade_by_stock_daily(fid_cond_mrkt_div_code, fid_input_iscd[, +1 opt])` | 종목별 프로그램매매추이(일별) [국내주식-113] | FHPPG04650201 | `/uapi/domestic-stock/v1/quotations/program-trade-by-stock-daily` |
| `psearch_result(user_id, seq)` | 종목조건검색조회 [국내주식-039] | HHKST03900400 | `/uapi/domestic-stock/v1/quotations/psearch-result` |
| `psearch_title(user_id)` | 종목조건검색 목록조회[국내주식-038] | HHKST03900300 | `/uapi/domestic-stock/v1/quotations/psearch-title` |
| `tradprt_byamt(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd)` | 국내주식 체결금액별 매매비중 [국내주식-192] | FHKST111900C0 | `/uapi/domestic-stock/v1/quotations/tradprt-byamt` |

## 실시간시세

| 함수 원형 | 설명 | tr_id | URL |
|---|---|---|---|
| `asking_price_krx(tr_type, tr_key[, +1 opt])` | 국내주식 실시간호가 (KRX) [실시간-004] | H0STASP0 | `(웹소켓)` |
| `asking_price_nxt(tr_type, tr_key)` | 국내주식 실시간호가 (NXT) | H0NXASP0 | `(웹소켓)` |
| `asking_price_total(tr_type, tr_key)` | 국내주식 실시간호가 (통합) | H0UNASP0 | `(웹소켓)` |
| `ccnl_krx(tr_type, tr_key[, +1 opt])` | 국내주식 실시간체결가(KRX) [실시간-003] | H0STCNT0 | `(웹소켓)` |
| `ccnl_notice(tr_type, tr_key[, +1 opt])` | 국내주식 주식체결통보 [실시간-005] | H0STCNI0, H0STCNI9 | `(웹소켓)` |
| `ccnl_nxt(tr_type, tr_key)` | 국내주식 실시간체결가 (NXT) | H0NXCNT0 | `(웹소켓)` |
| `ccnl_total(tr_type, tr_key)` | 국내주식 실시간체결가 (통합) | H0UNCNT0 | `(웹소켓)` |
| `exp_ccnl_krx(tr_type, tr_key)` | 국내주식 실시간예상체결 (KRX) [실시간-041] | H0STANC0 | `(웹소켓)` |
| `exp_ccnl_nxt(tr_type, tr_key)` | 국내주식 실시간예상체결 (NXT) | H0NXANC0 | `(웹소켓)` |
| `exp_ccnl_total(tr_type, tr_key)` | 국내주식 실시간예상체결(통합) | H0UNANC0 | `(웹소켓)` |
| `index_ccnl(tr_type, tr_key)` | 국내지수 실시간체결 [실시간-026] | H0UPCNT0 | `(웹소켓)` |
| `index_exp_ccnl(tr_type, tr_key)` | 국내지수 실시간예상체결 [실시간-027] | H0UPANC0 | `(웹소켓)` |
| `index_program_trade(tr_type, tr_key)` | 국내지수 실시간프로그램매매 [실시간-028] | H0UPPGM0 | `(웹소켓)` |
| `market_status_krx(tr_type, tr_key)` | 국내주식 장운영정보 (KRX) [실시간-049] | H0STMKO0 | `(웹소켓)` |
| `market_status_nxt(tr_type, tr_key)` | 국내주식 장운영정보(NXT) | H0NXMKO0 | `(웹소켓)` |
| `market_status_total(tr_type, tr_key)` | 국내주식 장운영정보(통합) | H0UNMKO0 | `(웹소켓)` |
| `member_krx(tr_type, tr_key)` | 국내주식 실시간회원사 (KRX) [실시간-047] | H0STMBC0 | `(웹소켓)` |
| `member_nxt(tr_type, tr_key)` | 국내주식 실시간회원사 (NXT) | H0NXMBC0 | `(웹소켓)` |
| `member_total(tr_type, tr_key)` | 국내주식 실시간회원사 (통합) | H0UNMBC0 | `(웹소켓)` |
| `overtime_asking_price_krx(tr_type, tr_key)` | 국내주식 시간외 실시간호가 (KRX) [실시간-025] | H0STOAA0 | `(웹소켓)` |
| `overtime_ccnl_krx(tr_type, tr_key)` | 국내주식 시간외 실시간체결가 (KRX) [실시간-042] | H0STOUP0 | `(웹소켓)` |
| `overtime_exp_ccnl_krx(tr_type, tr_key)` | 국내주식 시간외 실시간예상체결 (KRX) [실시간-024] | H0STOAC0 | `(웹소켓)` |
| `program_trade_krx(tr_type, tr_key)` | 국내주식 실시간프로그램매매 (KRX)  [실시간-048] | H0STPGM0 | `(웹소켓)` |
| `program_trade_nxt(tr_type, tr_key)` | 국내주식 실시간프로그램매매 (NXT) | H0NXPGM0 | `(웹소켓)` |
| `program_trade_total(tr_type, tr_key)` | 국내주식 실시간프로그램매매 (통합) | H0UNPGM0 | `(웹소켓)` |

## 업종/기타

| 함수 원형 | 설명 | tr_id | URL |
|---|---|---|---|
| `chk_holiday(bass_dt[, +6 opt])` | 국내휴장일조회[국내주식-040] | CTCA0903R | `/uapi/domestic-stock/v1/quotations/chk-holiday` |
| `comp_interest(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_div_cls_code, fid_div_cls_code1[, +5 opt])` | 금리 종합(국내채권_금리)[국내주식-155] | FHPST07020000 | `/uapi/domestic-stock/v1/quotations/comp-interest` |
| `exp_index_trend(fid_mkop_cls_code, fid_input_hour_1, fid_input_iscd, fid_cond_mrkt_div_code[, +4 opt])` | 국내주식 예상체결지수 추이[국내주식-121] | FHPST01840000 | `/uapi/domestic-stock/v1/quotations/exp-index-trend` |
| `exp_total_index(fid_mrkt_cls_code, fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_mkop_cls_code[, +5 opt])` | 국내주식 예상체결 전체지수[국내주식-122] | FHKUP11750000 | `/uapi/domestic-stock/v1/quotations/exp-total-index` |
| `inquire_index_category_price(fid_cond_mrkt_div_code, fid_input_iscd, fid_cond_scr_div_code, fid_mrkt_cls_code, fid_blng_cls_code[, +5 opt])` | 국내업종 구분별전체시세[v1_국내주식-066] | FHPUP02140000 | `/uapi/domestic-stock/v1/quotations/inquire-index-category-price` |
| `inquire_index_daily_price(fid_period_div_code, fid_cond_mrkt_div_code, fid_input_iscd, fid_input_date_1[, +5 opt])` | 국내업종 일자별지수 [v1_국내주식-065] | FHPUP02120000 | `/uapi/domestic-stock/v1/quotations/inquire-index-daily-price` |
| `inquire_index_price(fid_cond_mrkt_div_code, fid_input_iscd[, +4 opt])` | 국내업종 현재지수 [v1_국내주식-063] | FHPUP02100000 | `/uapi/domestic-stock/v1/quotations/inquire-index-price` |
| `inquire_index_tickprice(fid_input_iscd, fid_cond_mrkt_div_code[, +4 opt])` | 국내업종 시간별지수(초)[국내주식-064] | FHPUP02110100 | `/uapi/domestic-stock/v1/quotations/inquire-index-tickprice` |
| `inquire_index_timeprice(fid_input_hour_1, fid_input_iscd, fid_cond_mrkt_div_code[, +4 opt])` | 국내업종 시간별지수(분)[국내주식-119] | FHPUP02110200 | `/uapi/domestic-stock/v1/quotations/inquire-index-timeprice` |
| `market_time()` | 국내선물 영업일조회 [국내주식-160] | HHMCM000002C0 | `/uapi/domestic-stock/v1/quotations/market-time` |

## 종목정보

| 함수 원형 | 설명 | tr_id | URL |
|---|---|---|---|
| `credit_by_company(fid_rank_sort_cls_code, fid_slct_yn, fid_input_iscd, fid_cond_scr_div_code, fid_cond_mrkt_div_code[, +4 opt])` | 국내주식 당사 신용가능종목[국내주식-111] | FHPST04770000 | `/uapi/domestic-stock/v1/quotations/credit-by-company` |
| `estimate_perform(sht_cd[, +7 opt])` | 국내주식 종목추정실적[국내주식-187] | HHKST668300C0 | `/uapi/domestic-stock/v1/quotations/estimate-perform` |
| `finance_balance_sheet(fid_div_cls_code, fid_cond_mrkt_div_code, fid_input_iscd[, +4 opt])` | 국내주식 대차대조표 [v1_국내주식-078] | FHKST66430100 | `/uapi/domestic-stock/v1/finance/balance-sheet` |
| `finance_financial_ratio(fid_div_cls_code, fid_cond_mrkt_div_code, fid_input_iscd[, +4 opt])` | 국내주식 재무비율 [v1_국내주식-080] | FHKST66430300 | `/uapi/domestic-stock/v1/finance/financial-ratio` |
| `finance_growth_ratio(fid_input_iscd, fid_div_cls_code, fid_cond_mrkt_div_code[, +4 opt])` | 국내주식 성장성비율 [v1_국내주식-085] | FHKST66430800 | `/uapi/domestic-stock/v1/finance/growth-ratio` |
| `finance_income_statement(fid_div_cls_code, fid_cond_mrkt_div_code, fid_input_iscd[, +4 opt])` | 국내주식 손익계산서 [v1_국내주식-079] | FHKST66430200 | `/uapi/domestic-stock/v1/finance/income-statement` |
| `finance_other_major_ratios(fid_input_iscd, fid_div_cls_code, fid_cond_mrkt_div_code[, +4 opt])` | 국내주식 기타주요비율[v1_국내주식-082] | FHKST66430500 | `/uapi/domestic-stock/v1/finance/other-major-ratios` |
| `finance_profit_ratio(fid_input_iscd, fid_div_cls_code, fid_cond_mrkt_div_code[, +4 opt])` | 국내주식 수익성비율[v1_국내주식-081] | FHKST66430400 | `/uapi/domestic-stock/v1/finance/profit-ratio` |
| `finance_stability_ratio(fid_input_iscd, fid_div_cls_code, fid_cond_mrkt_div_code[, +4 opt])` | 국내주식 안정성비율[v1_국내주식-083] | FHKST66430600 | `/uapi/domestic-stock/v1/finance/stability-ratio` |
| `invest_opbysec(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_div_cls_code, fid_input_date_1, fid_input_date_2[, +4 opt])` | 국내주식 증권사별 투자의견[국내주식-189] | FHKST663400C0 | `/uapi/domestic-stock/v1/quotations/invest-opbysec` |
| `invest_opinion(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_iscd, fid_input_date_1, fid_input_date_2[, +4 opt])` | 국내주식 종목투자의견[국내주식-188] | FHKST663300C0 | `/uapi/domestic-stock/v1/quotations/invest-opinion` |
| `ksdinfo_bonus_issue(cts, f_dt, t_dt, sht_cd[, +4 opt])` | 예탁원정보(무상증자일정)[국내주식-144] | HHKDB669101C0 | `/uapi/domestic-stock/v1/ksdinfo/bonus-issue` |
| `ksdinfo_cap_dcrs(cts, f_dt, t_dt, sht_cd[, +4 opt])` | 예탁원정보(자본감소일정) [국내주식-149] | HHKDB669106C0 | `/uapi/domestic-stock/v1/ksdinfo/cap-dcrs` |
| `ksdinfo_dividend(cts, gb1, f_dt, t_dt, sht_cd, high_gb[, +4 opt])` | 예탁원정보(배당일정)[국내주식-145] | HHKDB669102C0 | `/uapi/domestic-stock/v1/ksdinfo/dividend` |
| `ksdinfo_forfeit(sht_cd, t_dt, f_dt, cts[, +4 opt])` | 예탁원정보(실권주일정)[국내주식-152] | HHKDB669109C0 | `/uapi/domestic-stock/v1/ksdinfo/forfeit` |
| `ksdinfo_list_info(sht_cd, t_dt, f_dt, cts[, +4 opt])` | 예탁원정보(상장정보일정)[국내주식-150] | HHKDB669107C0 | `/uapi/domestic-stock/v1/ksdinfo/list-info` |
| `ksdinfo_mand_deposit(t_dt, sht_cd, f_dt, cts[, +4 opt])` | 예탁원정보(의무예치일정) [국내주식-153] | HHKDB669110C0 | `/uapi/domestic-stock/v1/ksdinfo/mand-deposit` |
| `ksdinfo_merger_split(cts, f_dt, t_dt, sht_cd[, +4 opt])` | 예탁원정보(합병_분할일정)[국내주식-147] | HHKDB669104C0 | `/uapi/domestic-stock/v1/ksdinfo/merger-split` |
| `ksdinfo_paidin_capin(cts, gb1, f_dt, t_dt, sht_cd[, +4 opt])` | 예탁원정보(유상증자일정)[국내주식-143] | HHKDB669100C0 | `/uapi/domestic-stock/v1/ksdinfo/paidin-capin` |
| `ksdinfo_pub_offer(sht_cd, cts, f_dt, t_dt[, +4 opt])` | 예탁원정보(공모주청약일정)[국내주식-151] | HHKDB669108C0 | `/uapi/domestic-stock/v1/ksdinfo/pub-offer` |
| `ksdinfo_purreq(sht_cd, t_dt, f_dt, cts[, +4 opt])` | 예탁원정보(주식매수청구일정)[국내주식-146] | HHKDB669103C0 | `/uapi/domestic-stock/v1/ksdinfo/purreq` |
| `ksdinfo_rev_split(sht_cd, cts, f_dt, t_dt, market_gb[, +4 opt])` | 예탁원정보(액면교체일정)[국내주식-148] | HHKDB669105C0 | `/uapi/domestic-stock/v1/ksdinfo/rev-split` |
| `ksdinfo_sharehld_meet(cts, f_dt, t_dt, sht_cd[, +4 opt])` | 예탁원정보(주주총회일정)[국내주식-154] | HHKDB669111C0 | `/uapi/domestic-stock/v1/ksdinfo/sharehld-meet` |
| `lendable_by_company(excg_dvsn_cd, pdno, thco_stln_psbl_yn, inqr_dvsn_1, ctx_area_fk200, ctx_area_nk100[, +5 opt])` | 당사 대주가능 종목 [국내주식-195] | CTSC2702R | `/uapi/domestic-stock/v1/quotations/lendable-by-company` |
| `news_title(fid_news_ofer_entp_code, fid_cond_mrkt_cls_code, fid_input_iscd, fid_titl_cntt, fid_input_date_1, fid_input_hour_1, fid_rank_sort_cls_code, fid_input_srno[, +4 opt])` | 종합 시황/공시(제목) [국내주식-141] | FHKST01011800 | `/uapi/domestic-stock/v1/quotations/news-title` |
| `search_info(pdno, prdt_type_cd[, +4 opt])` | 상품기본조회[v1_국내주식-029] | CTPF1604R | `/uapi/domestic-stock/v1/quotations/search-info` |
| `search_stock_info(prdt_type_cd, pdno[, +4 opt])` | 주식기본조회[v1_국내주식-067] | CTPF1002R | `/uapi/domestic-stock/v1/quotations/search-stock-info` |

## 주문/계좌

| 함수 원형 | 설명 | tr_id | URL |
|---|---|---|---|
| `inquire_account_balance(cano, acnt_prdt_cd[, +2 opt])` | 투자계좌자산현황조회[v1_국내주식-048] | CTRP6548R | `/uapi/domestic-stock/v1/trading/inquire-account-balance` |
| `inquire_balance(env_dv, cano, acnt_prdt_cd, afhr_flpr_yn, inqr_dvsn, unpr_dvsn, fund_sttl_icld_yn, fncg_amt_auto_rdpt_yn, prcs_dvsn[, +7 opt])` | 주식잔고조회[v1_국내주식-006] | TTTC8434R, VTTC8434R | `/uapi/domestic-stock/v1/trading/inquire-balance` |
| `inquire_balance_rlz_pl(cano, acnt_prdt_cd, afhr_flpr_yn, inqr_dvsn, unpr_dvsn, fund_sttl_icld_yn, fncg_amt_auto_rdpt_yn, prcs_dvsn[, +9 opt])` | 주식잔고조회_실현손익[v1_국내주식-041] | TTTC8494R | `/uapi/domestic-stock/v1/trading/inquire-balance-rlz-pl` |
| `inquire_credit_psamount(cano, acnt_prdt_cd, pdno, ord_dvsn, crdt_type, cma_evlu_amt_icld_yn, ovrs_icld_yn[, +1 opt])` | 신용매수가능조회[v1_국내주식-042] | TTTC8909R | `/uapi/domestic-stock/v1/trading/inquire-credit-psamount` |
| `inquire_daily_ccld(env_dv, pd_dv, cano, acnt_prdt_cd, inqr_strt_dt, inqr_end_dt, sll_buy_dvsn_cd, ccld_dvsn, inqr_dvsn, inqr_dvsn_3[, +12 opt])` | 주식일별주문체결조회[v1_국내주식-005] | CTSC9215R, TTTC0081R, VTSC9215R, VTTC0081R | `/uapi/domestic-stock/v1/trading/inquire-daily-ccld` |
| `inquire_period_profit(cano, acnt_prdt_cd, inqr_strt_dt, inqr_end_dt, sort_dvsn, inqr_dvsn, cblc_dvsn[, +8 opt])` | 기간별손익일별합산조회[v1_국내주식-052] | TTTC8708R | `/uapi/domestic-stock/v1/trading/inquire-period-profit` |
| `inquire_period_trade_profit(cano, acnt_prdt_cd, sort_dvsn, inqr_strt_dt, inqr_end_dt, cblc_dvsn[, +8 opt])` | 기간별매매손익현황조회[v1_국내주식-060] | TTTC8715R | `/uapi/domestic-stock/v1/trading/inquire-period-trade-profit` |
| `inquire_psbl_order(env_dv, cano, acnt_prdt_cd, pdno, ord_unpr, ord_dvsn, cma_evlu_amt_icld_yn, ovrs_icld_yn)` | 매수가능조회[v1_국내주식-007] | TTTC8908R, VTTC8908R | `/uapi/domestic-stock/v1/trading/inquire-psbl-order` |
| `inquire_psbl_rvsecncl(cano, acnt_prdt_cd, inqr_dvsn_1, inqr_dvsn_2[, +6 opt])` | 주식정정취소가능주문조회[v1_국내주식-004] | TTTC0084R | `/uapi/domestic-stock/v1/trading/inquire-psbl-rvsecncl` |
| `inquire_psbl_sell(cano, acnt_prdt_cd, pdno[, +4 opt])` | 매도가능수량조회 [국내주식-165] | TTTC8408R | `/uapi/domestic-stock/v1/trading/inquire-psbl-sell` |
| `intgr_margin(cano, acnt_prdt_cd, cma_evlu_amt_icld_yn, wcrc_frcr_dvsn_cd, fwex_ctrt_frcr_dvsn_cd)` | 주식통합증거금 현황 [국내주식-191] | TTTC0869R | `/uapi/domestic-stock/v1/trading/intgr-margin` |
| `order_cash(env_dv, ord_dv, cano, acnt_prdt_cd, pdno, ord_dvsn, ord_qty, ord_unpr, excg_id_dvsn_cd[, +2 opt])` | 주식주문(현금)[v1_국내주식-001] | TTTC0011U, TTTC0012U, VTTC0011U, VTTC0012U | `/uapi/domestic-stock/v1/trading/order-cash` |
| `order_credit(ord_dv, cano, acnt_prdt_cd, pdno, crdt_type, loan_dt, ord_dvsn, ord_qty, ord_unpr[, +16 opt])` | 주식주문(신용)[v1_국내주식-002] | TTTC0051U, TTTC0052U | `/uapi/domestic-stock/v1/trading/order-credit` |
| `order_resv(cano, acnt_prdt_cd, pdno, ord_qty, ord_unpr, sll_buy_dvsn_cd, ord_dvsn_cd, ord_objt_cblc_dvsn_cd[, +3 opt])` | 주식예약주문[v1_국내주식-017] | CTSC0008U | `/uapi/domestic-stock/v1/trading/order-resv` |
| `order_resv_ccnl(rsvn_ord_ord_dt, rsvn_ord_end_dt, tmnl_mdia_kind_cd, cano, acnt_prdt_cd, prcs_dvsn_cd, cncl_yn[, +9 opt])` | 주식예약주문조회[v1_국내주식-020] | CTSC0004R | `/uapi/domestic-stock/v1/trading/order-resv-ccnl` |
| `order_resv_rvsecncl(cano, acnt_prdt_cd, rsvn_ord_seq, rsvn_ord_orgno, rsvn_ord_ord_dt, ord_type[, +9 opt])` | 주식예약주문정정취소[v1_국내주식-018,019] | CTSC0009U, CTSC0013U | `/uapi/domestic-stock/v1/trading/order-resv-rvsecncl` |
| `order_rvsecncl(env_dv, cano, acnt_prdt_cd, krx_fwdg_ord_orgno, orgn_odno, ord_dvsn, rvse_cncl_dvsn_cd, ord_qty, ord_unpr, qty_all_ord_yn, excg_id_dvsn_cd[, +1 opt])` | 주식주문(정정취소)[v1_국내주식-003] | TTTC0013U, VTTC0013U | `/uapi/domestic-stock/v1/trading/order-rvsecncl` |
| `pension_inquire_balance(cano, acnt_prdt_cd, acca_dvsn_cd, inqr_dvsn[, +7 opt])` | 퇴직연금 잔고조회[v1_국내주식-036] | TTTC2208R | `/uapi/domestic-stock/v1/trading/pension/inquire-balance` |
| `pension_inquire_daily_ccld(cano, acnt_prdt_cd, user_dvsn_cd, sll_buy_dvsn_cd, ccld_nccs_dvsn, inqr_dvsn_3[, +6 opt])` | 퇴직연금 미체결내역[v1_국내주식-033] | TTTC2201R | `/uapi/domestic-stock/v1/trading/pension/inquire-daily-ccld` |
| `pension_inquire_deposit(cano, acnt_prdt_cd, acca_dvsn_cd)` | 퇴직연금 예수금조회[v1_국내주식-035] | TTTC0506R | `/uapi/domestic-stock/v1/trading/pension/inquire-deposit` |
| `pension_inquire_present_balance(cano, acnt_prdt_cd, user_dvsn_cd[, +2 opt])` | 퇴직연금 체결기준잔고[v1_국내주식-032] | TTTC2202R | `/uapi/domestic-stock/v1/trading/pension/inquire-present-balance` |
| `pension_inquire_psbl_order(cano, acnt_prdt_cd, pdno, acca_dvsn_cd, cma_evlu_amt_icld_yn, ord_unpr, ord_dvsn)` | 퇴직연금 매수가능조회[v1_국내주식-034] | TTTC0503R | `/uapi/domestic-stock/v1/trading/pension/inquire-psbl-order` |
| `period_rights(inqr_dvsn, cano, acnt_prdt_cd, inqr_strt_dt, inqr_end_dt[, +11 opt])` | 기간별계좌권리현황조회 [국내주식-211] | CTRGA011R | `/uapi/domestic-stock/v1/trading/period-rights` |
