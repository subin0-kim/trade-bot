---
name: kis-api-overseas-stock
scope: shared
updated: 2026-07-26
sources:
  - ../open-trading-api/examples_llm/overseas_stock/ (자동 생성: scripts/gen_kis_api_catalog.py)
---

# KIS API 카탈로그 — 해외주식 (50개)

> 전체 스펙(전 파라미터·응답 필드)은 `../open-trading-api/examples_llm/overseas_stock/<함수명>/` 참조.
> 시그니처의 `[, +N opt]`는 생략 가능한 파라미터 개수. tr_id 첫 글자 T/J/C는 모의투자에서 V로 치환됨 ([[kis-api-notes]]).

## 기본시세

| 함수 원형 | 설명 | tr_id | URL |
|---|---|---|---|
| `countries_holiday(trad_dt[, +6 opt])` | 해외결제일자조회[해외주식-017] | CTOS5011R | `/uapi/overseas-stock/v1/quotations/countries-holiday` |
| `dailyprice(auth, excd, symb, gubn, bymd, modp[, +6 opt])` | 해외주식 기간별시세[v1_해외주식-010] | HHDFS76240000 | `/uapi/overseas-price/v1/quotations/dailyprice` |
| `industry_price(excd[, +6 opt])` | 해외주식 업종별코드조회[해외주식-049] | HHDFS76370100 | `/uapi/overseas-price/v1/quotations/industry-price` |
| `industry_theme(excd, icod, vol_rang[, +7 opt])` | 해외주식 업종별시세[해외주식-048] | HHDFS76370000 | `/uapi/overseas-price/v1/quotations/industry-theme` |
| `inquire_asking_price(auth, excd, symb[, +6 opt])` | 해외주식 현재가 1호가[해외주식-033] | HHDFS76200100 | `/uapi/overseas-price/v1/quotations/inquire-asking-price` |
| `inquire_daily_chartprice(fid_cond_mrkt_div_code, fid_input_iscd, fid_input_date_1, fid_input_date_2, fid_period_div_code[, +6 opt])` | 해외주식 종목_지수_환율기간별시세(일_주_월_년)[v1_해외주식-012] | FHKST03030100 | `/uapi/overseas-price/v1/quotations/inquire-daily-chartprice` |
| `inquire_time_indexchartprice(fid_cond_mrkt_div_code, fid_input_iscd, fid_hour_cls_code, fid_pw_data_incu_yn[, +5 opt])` | 해외지수분봉조회[v1_해외주식-031] | FHKST03030200 | `/uapi/overseas-price/v1/quotations/inquire-time-indexchartprice` |
| `inquire_time_itemchartprice(auth, excd, symb, nmin, pinc, next, nrec, fill, keyb[, +5 opt])` | 해외주식분봉조회[v1_해외주식-030] | HHDFS76950200 | `/uapi/overseas-price/v1/quotations/inquire-time-itemchartprice` |
| `price(auth, excd, symb[, +5 opt])` | 해외주식 현재체결가[v1_해외주식-009] | HHDFS00000300 | `/uapi/overseas-price/v1/quotations/price` |
| `price_detail(auth, excd, symb[, +4 opt])` | 해외주식 현재가상세[v1_해외주식-029] | HHDFS76200200 | `/uapi/overseas-price/v1/quotations/price-detail` |
| `quot_inquire_ccnl(excd, tday, symb[, +6 opt])` | 해외주식 체결추이[해외주식-037] | HHDFS76200300 | `/uapi/overseas-price/v1/quotations/inquire-ccnl` |

## 기타

| 함수 원형 | 설명 | tr_id | URL |
|---|---|---|---|
| `foreign_margin(cano, acnt_prdt_cd[, +4 opt])` | [해외주식] 주문/계좌 | TTTC2101R | `/uapi/overseas-stock/v1/trading/foreign-margin` |

## 시세분석

| 함수 원형 | 설명 | tr_id | URL |
|---|---|---|---|
| `brknews_title(fid_news_ofer_entp_code, fid_cond_scr_div_code[, +7 opt])` | 해외속보(제목) [해외주식-055] | FHKST01011801 | `/uapi/overseas-price/v1/quotations/brknews-title` |
| `colable_by_company(pdno, natn_cd, inqr_sqn_dvsn[, +14 opt])` | 당사 해외주식담보대출 가능 종목 [해외주식-051] | CTLN4050R | `/uapi/overseas-price/v1/quotations/colable-by-company` |
| `inquire_search(auth, excd, co_yn_pricecur, co_st_pricecur, co_en_pricecur, co_yn_rate, co_st_rate, co_en_rate, co_yn_valx, co_st_valx, co_en_valx, co_yn_shar, co_st_shar, co_en_shar, co_yn_volume, co_st_volume, co_en_volume, co_yn_amt, co_st_amt, co_en_amt, co_yn_eps, co_st_eps, co_en_eps, co_yn_per, co_st_per, co_en_per, keyb[, +5 opt])` | 해외주식조건검색[v1_해외주식-015] | HHDFS76410000 | `/uapi/overseas-price/v1/quotations/inquire-search` |
| `market_cap(excd, vol_rang[, +7 opt])` | 해외주식 시가총액순위[해외주식-047] | HHDFS76350100 | `/uapi/overseas-stock/v1/ranking/market-cap` |
| `new_highlow(excd, minx, vol_rang, gubn, gubn2[, +7 opt])` | 해외주식 신고/신저가[해외주식-042] | HHDFS76300000 | `/uapi/overseas-stock/v1/ranking/new-highlow` |
| `news_title([, +12 opt])` | 해외뉴스종합(제목) [해외주식-053] | HHPSTH60100C1 | `/uapi/overseas-price/v1/quotations/news-title` |
| `period_rights(rght_type_cd, inqr_dvsn_cd, inqr_strt_dt, inqr_end_dt[, +8 opt])` | 해외주식 기간별권리조회 [해외주식-052] | CTRGT011R | `/uapi/overseas-price/v1/quotations/period-rights` |
| `price_fluct(excd, gubn, minx, vol_rang[, +7 opt])` | 해외주식 가격급등락[해외주식-038] | HHDFS76260000 | `/uapi/overseas-stock/v1/ranking/price-fluct` |
| `rights_by_ice(ncod, symb[, +2 opt])` | 해외주식 권리종합 [해외주식-050] | HHDFS78330900 | `/uapi/overseas-price/v1/quotations/rights-by-ice` |
| `search_info(prdt_type_cd, pdno[, +4 opt])` | 해외주식 상품기본정보[v1_해외주식-034] | CTPF1702R | `/uapi/overseas-price/v1/quotations/search-info` |
| `trade_growth(excd, nday, vol_rang[, +7 opt])` | 해외주식 거래증가율순위[해외주식-045] | HHDFS76330000 | `/uapi/overseas-stock/v1/ranking/trade-growth` |
| `trade_pbmn(excd, nday, vol_rang[, +9 opt])` | 해외주식 거래대금순위[해외주식-044] | HHDFS76320010 | `/uapi/overseas-stock/v1/ranking/trade-pbmn` |
| `trade_turnover(excd, nday, vol_rang[, +7 opt])` | 해외주식 거래회전율순위[해외주식-046] | HHDFS76340000 | `/uapi/overseas-stock/v1/ranking/trade-turnover` |
| `trade_vol(excd, nday, vol_rang[, +9 opt])` | 해외주식 거래량순위[해외주식-043] | HHDFS76310010 | `/uapi/overseas-stock/v1/ranking/trade-vol` |
| `updown_rate(excd, nday, gubn, vol_rang[, +7 opt])` | 해외주식 상승률/하락률[해외주식-041] | HHDFS76290000 | `/uapi/overseas-stock/v1/ranking/updown-rate` |
| `volume_power(excd, nday, vol_rang[, +7 opt])` | 해외주식 매수체결강도상위[해외주식-040] | HHDFS76280000 | `/uapi/overseas-stock/v1/ranking/volume-power` |
| `volume_surge(excd, minx, vol_rang[, +7 opt])` | 해외주식 거래량급증[해외주식-039] | HHDFS76270000 | `/uapi/overseas-stock/v1/ranking/volume-surge` |

## 실시간시세

| 함수 원형 | 설명 | tr_id | URL |
|---|---|---|---|
| `asking_price(tr_type, tr_key)` | 해외주식 실시간호가[실시간-021] | HDFSASP0 | `(웹소켓)` |
| `ccnl_notice(tr_type, tr_key, env_dv)` | 해외주식 실시간체결통보[실시간-009] | H0GSCNI0, H0GSCNI9 | `(웹소켓)` |
| `delayed_asking_price_asia(tr_type, tr_key)` | 해외주식 지연호가(아시아)[실시간-008] | HDFSASP1 | `(웹소켓)` |
| `delayed_ccnl(tr_type, tr_key)` | 해외주식 실시간지연체결가[실시간-007] | HDFSCNT0 | `(웹소켓)` |

## 주문/계좌

| 함수 원형 | 설명 | tr_id | URL |
|---|---|---|---|
| `algo_ordno(cano, acnt_prdt_cd, trad_dt[, +6 opt])` | 해외주식 지정가주문번호조회 [해외주식-071] | TTTS6058R | `/uapi/overseas-stock/v1/trading/algo-ordno` |
| `daytime_order(order_dv, cano, acnt_prdt_cd, ovrs_excg_cd, pdno, ord_qty, ovrs_ord_unpr, ctac_tlno, mgco_aptm_odno, ord_svr_dvsn_cd, ord_dvsn)` | 해외주식 미국주간주문 [v1_해외주식-026] | TTTS6036U, TTTS6037U | `/uapi/overseas-stock/v1/trading/daytime-order` |
| `daytime_order_rvsecncl(cano, acnt_prdt_cd, ovrs_excg_cd, pdno, orgn_odno, rvse_cncl_dvsn_cd, ord_qty, ovrs_ord_unpr, ctac_tlno, mgco_aptm_odno, ord_svr_dvsn_cd)` | 해외주식 미국주간정정취소 [v1_해외주식-027] | TTTS6038U | `/uapi/overseas-stock/v1/trading/daytime-order-rvsecncl` |
| `inquire_algo_ccnl(cano, acnt_prdt_cd[, +11 opt])` | 해외주식 지정가체결내역조회 [해외주식-070] | TTTS6059R | `/uapi/overseas-stock/v1/trading/inquire-algo-ccnl` |
| `inquire_balance(cano, acnt_prdt_cd, ovrs_excg_cd, tr_crcy_cd[, +8 opt])` | 해외주식 잔고 [v1_해외주식-006] | TTTS3012R, VTTS3012R | `/uapi/overseas-stock/v1/trading/inquire-balance` |
| `inquire_ccnl(cano, acnt_prdt_cd, pdno, ord_strt_dt, ord_end_dt, sll_buy_dvsn, ccld_nccs_dvsn, sort_sqn, ord_dt, ord_gno_brno, odno[, +8 opt])` | 해외주식 주문체결내역 [v1_해외주식-007] | TTTS3035R, VTTS3035R | `/uapi/overseas-stock/v1/trading/inquire-ccnl` |
| `inquire_nccs(cano, acnt_prdt_cd, ovrs_excg_cd, sort_sqn, FK200, NK200[, +5 opt])` | 해외주식 미체결내역 [v1_해외주식-005] | TTTS3018R | `/uapi/overseas-stock/v1/trading/inquire-nccs` |
| `inquire_paymt_stdr_balance(cano, acnt_prdt_cd, bass_dt, wcrc_frcr_dvsn_cd, inqr_dvsn_cd[, +6 opt])` | 해외주식 결제기준잔고 [해외주식-064] | CTRP6010R | `/uapi/overseas-stock/v1/trading/inquire-paymt-stdr-balance` |
| `inquire_period_profit(cano, acnt_prdt_cd, ovrs_excg_cd, natn_cd, crcy_cd, pdno, inqr_strt_dt, inqr_end_dt, wcrc_frcr_dvsn_cd, FK200, NK200[, +5 opt])` | 해외주식 기간손익 [v1_해외주식-032] | TTTS3039R | `/uapi/overseas-stock/v1/trading/inquire-period-profit` |
| `inquire_period_trans(cano, acnt_prdt_cd, erlm_strt_dt, erlm_end_dt, ovrs_excg_cd, pdno, sll_buy_dvsn_cd, loan_dvsn_cd, FK100, NK100[, +5 opt])` | 해외주식 일별거래내역 [해외주식-063] | CTOS4001R | `/uapi/overseas-stock/v1/trading/inquire-period-trans` |
| `inquire_present_balance(cano, acnt_prdt_cd, wcrc_frcr_dvsn_cd, natn_cd, tr_mket_cd, inqr_dvsn_cd[, +7 opt])` | 해외주식 체결기준현재잔고 [v1_해외주식-008] | CTRP6504R, VTRP6504R | `/uapi/overseas-stock/v1/trading/inquire-present-balance` |
| `inquire_psamount(cano, acnt_prdt_cd, ovrs_excg_cd, ovrs_ord_unpr, item_cd[, +5 opt])` | 해외주식 매수가능금액조회 [v1_해외주식-014] | TTTS3007R, VTTS3007R | `/uapi/overseas-stock/v1/trading/inquire-psamount` |
| `order(cano, acnt_prdt_cd, ovrs_excg_cd, pdno, ord_qty, ovrs_ord_unpr, ord_dv, ctac_tlno, mgco_aptm_odno, ord_svr_dvsn_cd, ord_dvsn[, +1 opt])` | 해외주식 주문 [v1_해외주식-001] | TTTS0202U, TTTS0304U, TTTS0305U, TTTS0307U, TTTS0308U, TTTS0310U, TTTS0311U, TTTS1001U, TTTS1002U, TTTS1005U, TTTT1002U, TTTT1006U, V | `/uapi/overseas-stock/v1/trading/order` |
| `order_resv(env_dv, ord_dv, cano, acnt_prdt_cd, pdno, ovrs_excg_cd, ft_ord_qty, ft_ord_unpr3[, +8 opt])` | 해외주식 예약주문접수[v1_해외주식-002] | TTTS3013U, TTTT3014U, TTTT3016U, VTTS3013U, VTTT3014U, VTTT3016U | `/uapi/overseas-stock/v1/trading/order-resv` |
| `order_resv_ccnl(env_dv, nat_dv, cano, acnt_prdt_cd, rsvn_ord_rcit_dt, ovrs_rsvn_odno)` | 해외주식 예약주문접수취소[v1_해외주식-004] | TTTT3017U, VTTT3017U | `/uapi/overseas-stock/v1/trading/order-resv-ccnl` |
| `order_resv_list(nat_dv, cano, acnt_prdt_cd, inqr_strt_dt, inqr_end_dt, inqr_dvsn_cd, ovrs_excg_cd[, +7 opt])` | 해외주식 예약주문조회[v1_해외주식-013] | TTTS3014R, TTTT3039R | `/uapi/overseas-stock/v1/trading/order-resv-list` |
| `order_rvsecncl(cano, acnt_prdt_cd, ovrs_excg_cd, pdno, orgn_odno, rvse_cncl_dvsn_cd, ord_qty, ovrs_ord_unpr, mgco_aptm_odno, ord_svr_dvsn_cd[, +1 opt])` | 해외주식 정정취소주문[v1_해외주식-003] | TTTT1004U, VTTT1004U | `/uapi/overseas-stock/v1/trading/order-rvsecncl` |
