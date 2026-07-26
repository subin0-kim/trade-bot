---
name: kis-api-etfetn
scope: shared
updated: 2026-07-26
sources:
  - ../open-trading-api/examples_llm/etfetn/ (자동 생성: scripts/gen_kis_api_catalog.py)
---

# KIS API 카탈로그 — ETF/ETN (6개)

> 전체 스펙(전 파라미터·응답 필드)은 `../open-trading-api/examples_llm/etfetn/<함수명>/` 참조.
> 시그니처의 `[, +N opt]`는 생략 가능한 파라미터 개수. tr_id 첫 글자 T/J/C는 모의투자에서 V로 치환됨 ([[kis-api-notes]]).

## 기본시세

| 함수 원형 | 설명 | tr_id | URL |
|---|---|---|---|
| `inquire_component_stock_price(fid_cond_mrkt_div_code, fid_input_iscd, fid_cond_scr_div_code)` | ETF 구성종목시세[국내주식-073] | FHKST121600C0 | `/uapi/etfetn/v1/quotations/inquire-component-stock-price` |
| `inquire_price(fid_cond_mrkt_div_code, fid_input_iscd)` | ETF/ETN 현재가[v1_국내주식-068] | FHPST02400000 | `/uapi/etfetn/v1/quotations/inquire-price` |
| `nav_comparison_daily_trend(fid_cond_mrkt_div_code, fid_input_iscd, fid_input_date_1, fid_input_date_2)` | NAV 비교추이(일)[v1_국내주식-071] | FHPST02440200 | `/uapi/etfetn/v1/quotations/nav-comparison-daily-trend` |
| `nav_comparison_time_trend(fid_cond_mrkt_div_code, fid_input_iscd, fid_hour_cls_code)` | NAV 비교추이(분)[v1_국내주식-070] | FHPST02440100 | `/uapi/etfetn/v1/quotations/nav-comparison-time-trend` |
| `nav_comparison_trend(fid_cond_mrkt_div_code, fid_input_iscd)` | NAV 비교추이(종목)[v1_국내주식-069] | FHPST02440000 | `/uapi/etfetn/v1/quotations/nav-comparison-trend` |

## 실시간시세

| 함수 원형 | 설명 | tr_id | URL |
|---|---|---|---|
| `etf_nav_trend(tr_type, tr_key)` | 국내ETF NAV추이[실시간-051] | H0STNAV0 | `(웹소켓)` |
