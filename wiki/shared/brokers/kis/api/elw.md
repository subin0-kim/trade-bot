---
name: kis-api-elw
scope: shared
updated: 2026-07-26
sources:
  - ../open-trading-api/examples_llm/elw/ (자동 생성: scripts/gen_kis_api_catalog.py)
---

# KIS API 카탈로그 — ELW (24개)

> 전체 스펙(전 파라미터·응답 필드)은 `../open-trading-api/examples_llm/elw/<함수명>/` 참조.
> 시그니처의 `[, +N opt]`는 생략 가능한 파라미터 개수. tr_id 첫 글자 T/J/C는 모의투자에서 V로 치환됨 ([[kis-api-notes]]).

## 기타

| 함수 원형 | 설명 | tr_id | URL |
|---|---|---|---|
| `compare_stocks(fid_cond_scr_div_code, fid_input_iscd[, +4 opt])` | [국내주식] ELW시세 | FHKEW151701C0 | `/uapi/elw/v1/quotations/compare-stocks` |
| `cond_search(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_rank_sort_cls_code, fid_input_cnt_1[, +57 opt])` | ELW 종목검색 API를 호출하여 조건에 맞는 ELW 종목 정보를 조회합니다. | FHKEW15100000 | `/uapi/elw/v1/quotations/cond-search` |
| `elw_asking_price(tr_type, tr_key)` | ELW 실시간호가[H0EWASP0] | H0EWASP0 | `(웹소켓)` |
| `elw_ccnl(tr_type, tr_key)` | ELW 실시간체결가[H0EWCNT0] 구독 함수 | H0EWCNT0 | `(웹소켓)` |
| `elw_exp_ccnl(tr_type, tr_key)` | ELW 실시간예상체결[H0EWANC0] | H0EWANC0 | `(웹소켓)` |
| `expiration_stocks(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_input_date_1, fid_input_date_2, fid_div_cls_code, fid_etc_cls_code, fid_unas_input_iscd, fid_input_iscd_2, fid_blng_cls_code, fid_input_option_1[, +4 opt])` | [국내주식] ELW시세 | FHKEW154700C0 | `/uapi/elw/v1/quotations/expiration-stocks` |
| `indicator(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_unas_input_iscd, fid_input_iscd, fid_div_cls_code, fid_input_price_1, fid_input_price_2, fid_input_vol_1, fid_input_vol_2, fid_rank_sort_cls_code, fid_blng_cls_code[, +4 opt])` | [국내주식] ELW시세 | FHPEW02790000 | `/uapi/elw/v1/ranking/indicator` |
| `indicator_trend_ccnl(fid_cond_mrkt_div_code, fid_input_iscd[, +4 opt])` | [국내주식] ELW시세 | FHPEW02740100 | `/uapi/elw/v1/quotations/indicator-trend-ccnl` |
| `indicator_trend_daily(fid_cond_mrkt_div_code, fid_input_iscd[, +4 opt])` | [국내주식] ELW시세 | FHPEW02740200 | `/uapi/elw/v1/quotations/indicator-trend-daily` |
| `indicator_trend_minute(fid_cond_mrkt_div_code, fid_input_iscd, fid_hour_cls_code, fid_pw_data_incu_yn[, +4 opt])` | [국내주식] ELW시세 | FHPEW02740300 | `/uapi/elw/v1/quotations/indicator-trend-minute` |
| `lp_trade_trend(fid_cond_mrkt_div_code, fid_input_iscd[, +5 opt])` | [국내주식] ELW시세 | FHPEW03760000 | `/uapi/elw/v1/quotations/lp-trade-trend` |
| `newly_listed(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_div_cls_code, fid_unas_input_iscd, fid_input_iscd_2, fid_input_date_1, fid_blng_cls_code[, +4 opt])` | [국내주식] ELW시세 | FHKEW154800C0 | `/uapi/elw/v1/quotations/newly-listed` |
| `quick_change(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_unas_input_iscd, fid_input_iscd, fid_mrkt_cls_code, fid_input_price_1, fid_input_price_2, fid_input_vol_1, fid_input_vol_2, fid_hour_cls_code, fid_input_hour_1, fid_input_hour_2, fid_rank_sort_cls_code, fid_blng_cls_code[, +4 opt])` | [국내주식] ELW시세 | FHPEW02870000 | `/uapi/elw/v1/ranking/quick-change` |
| `sensitivity(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_unas_input_iscd, fid_input_iscd, fid_div_cls_code, fid_input_price_1, fid_input_price_2, fid_input_vol_1, fid_input_vol_2, fid_rank_sort_cls_code, fid_input_rmnn_dynu_1, fid_input_date_1, fid_blng_cls_code[, +4 opt])` | [국내주식] ELW시세 | FHPEW02850000 | `/uapi/elw/v1/ranking/sensitivity` |
| `sensitivity_trend_ccnl(fid_cond_mrkt_div_code, fid_input_iscd[, +4 opt])` | [국내주식] ELW시세 | FHPEW02830100 | `/uapi/elw/v1/quotations/sensitivity-trend-ccnl` |
| `sensitivity_trend_daily(fid_cond_mrkt_div_code, fid_input_iscd[, +4 opt])` | [국내주식] ELW시세 | FHPEW02830200 | `/uapi/elw/v1/quotations/sensitivity-trend-daily` |
| `udrl_asset_list(fid_cond_scr_div_code, fid_rank_sort_cls_code, fid_input_iscd[, +4 opt])` | [국내주식] ELW시세 | FHKEW154100C0 | `/uapi/elw/v1/quotations/udrl-asset-list` |
| `udrl_asset_price(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_mrkt_cls_code, fid_input_iscd, fid_unas_input_iscd, fid_vol_cnt, fid_trgt_exls_cls_code, fid_input_price_1, fid_input_price_2, fid_input_vol_1, fid_input_vol_2, fid_input_rmnn_dynu_1, fid_input_rmnn_dynu_2, fid_option, fid_input_option_1, fid_input_option_2[, +4 opt])` | [국내주식] ELW시세 | FHKEW154101C0 | `/uapi/elw/v1/quotations/udrl-asset-price` |
| `updown_rate(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_unas_input_iscd, fid_input_iscd, fid_input_rmnn_dynu_1, fid_div_cls_code, fid_input_price_1, fid_input_price_2, fid_input_vol_1, fid_input_vol_2, fid_input_date_1, fid_rank_sort_cls_code, fid_blng_cls_code, fid_input_date_2[, +4 opt])` | [국내주식] ELW시세 | FHPEW02770000 | `/uapi/elw/v1/ranking/updown-rate` |
| `volatility_trend_ccnl(fid_cond_mrkt_div_code, fid_input_iscd[, +4 opt])` | [국내주식] ELW시세 | FHPEW02840100 | `/uapi/elw/v1/quotations/volatility-trend-ccnl` |
| `volatility_trend_daily(fid_cond_mrkt_div_code, fid_input_iscd[, +4 opt])` | [국내주식] ELW시세 | FHPEW02840200 | `/uapi/elw/v1/quotations/volatility-trend-daily` |
| `volatility_trend_minute(fid_cond_mrkt_div_code, fid_input_iscd, fid_hour_cls_code, fid_pw_data_incu_yn[, +4 opt])` | [국내주식] ELW시세 | FHPEW02840300 | `/uapi/elw/v1/quotations/volatility-trend-minute` |
| `volatility_trend_tick(fid_cond_mrkt_div_code, fid_input_iscd[, +4 opt])` | [국내주식] ELW시세 | FHPEW02840400 | `/uapi/elw/v1/quotations/volatility-trend-tick` |
| `volume_rank(fid_cond_mrkt_div_code, fid_cond_scr_div_code, fid_unas_input_iscd, fid_input_iscd, fid_input_rmnn_dynu_1, fid_div_cls_code, fid_input_price_1, fid_input_price_2, fid_input_vol_1, fid_input_vol_2, fid_input_date_1, fid_rank_sort_cls_code, fid_blng_cls_code, fid_input_iscd_2, fid_input_date_2[, +4 opt])` | [국내주식] ELW시세 | FHPEW02780000 | `/uapi/elw/v1/ranking/volume-rank` |
