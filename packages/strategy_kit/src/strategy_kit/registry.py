"""전략 레지스트리 — 설정(dict)만으로 전략을 정의·조립한다.

전략 추가 = PRESETS에 항목 추가 (코드 수정 없음).
유튜브 조사로 발굴한 전략도 이 스키마로 수치화해 등재한다.

설정 스키마:
{
  "entry":   {"type": "<모듈명>", ...파라미터},
  "filters": [{"type": ...}, ...],           # 생략 가능
  "exits":   [{"type": ...}, ...],           # 순서 = 판정 우선순위
  "sizer":   {"type": ...},
  "primary_tf": "D",                          # 기준 타임프레임
  "higher_tfs": ["W"],                        # 필요한 상위 TF (MTF 필터용)
  "tags": ["mean_reversion", ...],            # 레짐 매칭용 분류
}
"""

from __future__ import annotations

from . import entry as entry_mod
from . import exit as exit_mod
from . import filter as filter_mod
from . import sizing as sizing_mod
from .composite import CompositeStrategy

ENTRY_TYPES = {
    "bollinger_touch": entry_mod.BollingerTouchEntry,
    "rsi_rebound": entry_mod.RSIReboundEntry,
    "rsi_below": entry_mod.RSIBelowEntry,
    "ma_cross": entry_mod.MACrossEntry,
    "breakout": entry_mod.BreakoutEntry,
    "macd_cross": entry_mod.MACDCrossEntry,
    "volume_spike_reversal": entry_mod.VolumeSpikeReversalEntry,
    "bb_zone": entry_mod.BBZoneEntry,
    "rsi_bb_breakout": entry_mod.RSIBBBreakoutEntry,
    "rsi_signal_cross": entry_mod.RSISignalCrossEntry,
    "ichimoku_bounce": entry_mod.IchimokuCloudBounceEntry,
    "box_breakout": entry_mod.BoxBreakoutEntry,
    "n_day_low": entry_mod.NDayLowEntry,
    "ibs_below": entry_mod.IBSEntry,
    "consecutive_down": entry_mod.ConsecutiveDownEntry,
    "ichimoku_tk_cross": entry_mod.IchimokuTKCrossEntry,
    "ichimoku_kumo_breakout": entry_mod.IchimokuKumoBreakoutEntry,
    "volatility_breakout": entry_mod.VolatilityBreakoutEntry,
    "double_rsi_cross": entry_mod.DoubleRSICrossEntry,
}

FILTER_TYPES = {
    "adx": filter_mod.ADXFilter,
    "higher_tf_trend": filter_mod.HigherTFTrendFilter,
    "volume": filter_mod.VolumeFilter,
    "price_above_ma": filter_mod.PriceAboveMAFilter,
    "roc": filter_mod.ROCFilter,
    "ma_compare": filter_mod.MACompareFilter,
    "minervini": filter_mod.MinerviniTrendFilter,
    "clenow": filter_mod.ClenowMomentumFilter,
    "rsi_range": filter_mod.RSIRangeFilter,
    "above_cloud": filter_mod.AboveCloudFilter,
    "chikou": filter_mod.ChikouFilter,
}

EXIT_TYPES = {
    "fixed_stop_take": exit_mod.FixedStopTakeExit,
    "atr_trailing": exit_mod.ATRTrailingExit,
    "atr_stop": exit_mod.ATRStopExit,
    "time_stop": exit_mod.TimeStopExit,
    "ma_cross_exit": exit_mod.MACrossExit,
    "bollinger_mid_exit": exit_mod.BollingerMidExit,
    "donchian_exit": exit_mod.DonchianExit,
    "above_ma_exit": exit_mod.PriceAboveMAExit,
    "bb_band_exit": exit_mod.BBBandExit,
    "rsi_bb_exit": exit_mod.RSIBBExit,
    "rsi_level_exit": exit_mod.RSILevelExit,
    "rsi_above_exit": exit_mod.RSIAboveExit,
    "ichimoku_exit": exit_mod.IchimokuCloudExit,
    "n_day_high_exit": exit_mod.NDayHighExit,
    "ibs_above_exit": exit_mod.IBSExit,
    "new_day_exit": exit_mod.NewDayExit,
    "double_rsi_exit": exit_mod.DoubleRSICrossExit,
}

SIZER_TYPES = {
    "fixed_fraction": sizing_mod.FixedFractionSizer,
    "atr_risk": sizing_mod.ATRRiskSizer,
}


def _build(types: dict, spec: dict):
    kind = spec["type"]
    if kind not in types:
        raise ValueError(f"미등록 모듈: {kind} (가능: {list(types)})")
    params = {k: v for k, v in spec.items() if k != "type"}
    return types[kind](**params)


def build_strategy(name: str, config: dict) -> CompositeStrategy:
    return CompositeStrategy(
        name=name,
        entry=_build(ENTRY_TYPES, config["entry"]),
        filters=[_build(FILTER_TYPES, f) for f in config.get("filters", [])],
        exits=[_build(EXIT_TYPES, e) for e in config["exits"]],
        sizer=_build(SIZER_TYPES, config.get("sizer", {"type": "fixed_fraction"})),
    )


# ---------------------------------------------------------------------------
# 시드 전략 프리셋 — 배관 검증 + 조사 전략의 등재 예시.
# 백테스트 게이트를 통과하기 전까지는 어떤 것도 '검증된 전략'이 아니다.
# ---------------------------------------------------------------------------
PRESETS: dict[str, dict] = {
    # 평균회귀: 횡보장 가설
    "bb_meanrev": {
        "entry": {"type": "bollinger_touch", "period": 20, "k": 2.0},
        "filters": [{"type": "adx", "period": 14, "max_adx": 25}],
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 3.0, "take_pct": 99.0},  # 손절만
            {"type": "bollinger_mid_exit", "period": 20},
            {"type": "time_stop", "max_bars": 15},
        ],
        "sizer": {"type": "fixed_fraction", "fraction": 0.2},
        "primary_tf": "D", "higher_tfs": [],
        "tags": ["mean_reversion", "range"],
    },
    "rsi_rebound": {
        "entry": {"type": "rsi_rebound", "period": 14, "threshold": 30},
        "filters": [{"type": "price_above_ma", "period": 120}],  # 장기 상승 종목만
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 4.0, "take_pct": 8.0},
            {"type": "time_stop", "max_bars": 20},
        ],
        "sizer": {"type": "fixed_fraction", "fraction": 0.2},
        "primary_tf": "D", "higher_tfs": [],
        "tags": ["mean_reversion", "pullback"],
    },
    # 추세추종: 상승장 가설
    "ma_trend": {
        "entry": {"type": "ma_cross", "fast": 5, "slow": 20},
        "filters": [{"type": "adx", "period": 14, "min_adx": 20}],
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 5.0, "take_pct": 99.0},
            {"type": "ma_cross_exit", "fast": 5, "slow": 20},
        ],
        "sizer": {"type": "atr_risk", "risk_pct": 1.0, "atr_period": 14, "stop_mult": 2.0},
        "primary_tf": "D", "higher_tfs": [],
        "tags": ["trend_follow"],
    },
    "macd_trend_mtf": {
        "entry": {"type": "macd_cross"},
        "filters": [{"type": "higher_tf_trend", "tf": "W", "ma_period": 10}],  # 주봉 상승국면만
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 5.0, "take_pct": 99.0},
            {"type": "atr_trailing", "period": 14, "mult": 3.0},
        ],
        "sizer": {"type": "atr_risk", "risk_pct": 1.0},
        "primary_tf": "D", "higher_tfs": ["W"],
        "tags": ["trend_follow", "mtf"],
    },
    # 모멘텀/돌파: 변동성 확장 가설
    "breakout_momo": {
        "entry": {"type": "breakout", "lookback": 20},
        "filters": [{"type": "volume", "period": 20, "min_ratio": 1.5}],
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 4.0, "take_pct": 99.0},
            {"type": "atr_trailing", "period": 14, "mult": 2.5},
            {"type": "time_stop", "max_bars": 40},
        ],
        "sizer": {"type": "atr_risk", "risk_pct": 1.0},
        "primary_tf": "D", "higher_tfs": [],
        "tags": ["momentum", "breakout"],
    },
    "vol_spike_rebound": {
        "entry": {"type": "volume_spike_reversal", "vol_period": 20, "vol_mult": 2.5},
        "filters": [{"type": "price_above_ma", "period": 60}],
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 3.0, "take_pct": 6.0},
            {"type": "time_stop", "max_bars": 10},
        ],
        "sizer": {"type": "fixed_fraction", "fraction": 0.15},
        "primary_tf": "D", "higher_tfs": [],
        "tags": ["momentum", "volume"],
    },
    # ------------------------------------------------------------------
    # 문헌 전략 (2026-07 조사분 — 출처는 source 필드와 wiki 전략 페이지)
    # ------------------------------------------------------------------
    "connors_rsi2": {
        "entry": {"type": "rsi_below", "period": 2, "threshold": 10},
        "filters": [{"type": "price_above_ma", "period": 200}],
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 6.0, "take_pct": 99.0},
            {"type": "above_ma_exit", "period": 5},
            {"type": "time_stop", "max_bars": 10},
        ],
        "sizer": {"type": "fixed_fraction", "fraction": 0.2},
        "primary_tf": "D", "higher_tfs": [],
        "tags": ["mean_reversion", "pullback"],
        "source": "Connors & Alvarez, 'Short Term Trading Strategies That Work' (2008) — RSI(2)<10 & 200일선 위, MA5 복귀 청산",
    },
    "turtle_20_10": {
        "entry": {"type": "breakout", "lookback": 20},
        "filters": [],
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 6.0, "take_pct": 99.0},
            {"type": "donchian_exit", "lookback": 10},
        ],
        "sizer": {"type": "atr_risk", "risk_pct": 1.0, "atr_period": 20, "stop_mult": 2.0},
        "primary_tf": "D", "higher_tfs": [],
        "tags": ["trend_follow", "breakout"],
        "source": "Richard Dennis 터틀 규칙 System 1 (Curtis Faith, 'Way of the Turtle') — 20일 돌파 진입/10일 저점 청산/2N 리스크",
    },
    "high_52w_momo": {
        "entry": {"type": "breakout", "lookback": 250},
        "filters": [{"type": "volume", "period": 20, "min_ratio": 1.2}],
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 8.0, "take_pct": 99.0},
            {"type": "atr_trailing", "period": 14, "mult": 3.5},
        ],
        "sizer": {"type": "atr_risk", "risk_pct": 1.0},
        "primary_tf": "D", "higher_tfs": [],
        "tags": ["momentum", "breakout"],
        "source": "George & Hwang, 'The 52-Week High and Momentum Investing' (J. Finance 2004)의 일봉 근사",
    },
    "abs_momentum": {
        "entry": {"type": "ma_cross", "fast": 20, "slow": 60},
        "filters": [{"type": "roc", "period": 126, "min_roc": 0.0}],
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 7.0, "take_pct": 99.0},
            {"type": "ma_cross_exit", "fast": 20, "slow": 60},
        ],
        "sizer": {"type": "fixed_fraction", "fraction": 0.2},
        "primary_tf": "D", "higher_tfs": [],
        "tags": ["trend_follow"],
        "source": "Gary Antonacci, 'Dual Momentum Investing' (2014)의 절대 모멘텀을 일봉 근사 (6개월 ROC>0 필터)",
    },
    # ------------------------------------------------------------------
    # 유튜브 조사 전략 (2026-07 — 원 출처 영상은 wiki 전략 페이지에 기록)
    # ------------------------------------------------------------------
    "dbb_kathy": {
        "entry": {"type": "bb_zone", "period": 20, "k": 1.0},
        "filters": [],
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 5.0, "take_pct": 99.0},
            {"type": "bb_band_exit", "period": 20, "k": 1.0},
        ],
        "sizer": {"type": "fixed_fraction", "fraction": 0.2},
        "primary_tf": "D", "higher_tfs": [],
        "tags": ["trend_follow"],
        "source": "Kathy Lien Double Bollinger Band — 유튜브 골드핑거 '볼린저밴드에 RSI 하나만 섞으세요' (youtube.com/watch?v=9ewMLrv95io) 자막 분석",
    },
    "rsi_bb_gold": {
        "entry": {"type": "rsi_bb_breakout", "rsi_period": 14, "bb_period": 30},
        "filters": [{"type": "price_above_ma", "period": 50}],
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 5.0, "take_pct": 99.0},
            {"type": "rsi_bb_exit", "rsi_period": 14, "bb_period": 30},
        ],
        "sizer": {"type": "fixed_fraction", "fraction": 0.2},
        "primary_tf": "D", "higher_tfs": [],
        "tags": ["trend_follow", "momentum"],
        "source": "Kathy Lien RSI-BB 기법 — 유튜브 골드핑거 (youtube.com/watch?v=9ewMLrv95io): RSI(14)+BB(30,2σ) on RSI, 50일선 필터",
    },
    "yt_rsi_30_70": {
        "entry": {"type": "rsi_rebound", "period": 14, "threshold": 30},
        "filters": [],
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 5.0, "take_pct": 99.0},
            {"type": "rsi_level_exit", "rsi_period": 14, "level": 70},
            {"type": "time_stop", "max_bars": 40},
        ],
        "sizer": {"type": "fixed_fraction", "fraction": 0.2},
        "primary_tf": "D", "higher_tfs": [],
        "tags": ["mean_reversion"],
        "source": "유튜브 '고수들만 몰래 쓰는 MACD+RSI 돈복사 매매법' (youtube.com/watch?v=TWO4NeDg6O4) 자막 분석 — RSI30 상향돌파 매수, 70 하향이탈 매도",
    },
    "yt_rsi_50_trend": {
        "entry": {"type": "rsi_rebound", "period": 14, "threshold": 50},
        "filters": [],
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 5.0, "take_pct": 99.0},
            {"type": "rsi_level_exit", "rsi_period": 14, "level": 50},
        ],
        "sizer": {"type": "fixed_fraction", "fraction": 0.2},
        "primary_tf": "D", "higher_tfs": [],
        "tags": ["trend_follow"],
        "source": "유튜브 TWO4NeDg6O4 자막 분석 — RSI 50선을 추세 기준선으로: 상향돌파 매수/하향이탈 매도",
    },
    "yt_rsi_sigcross": {
        "entry": {"type": "rsi_signal_cross", "rsi_period": 14, "signal_period": 14, "max_signal": 40},
        "filters": [],
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 4.0, "take_pct": 99.0},
            {"type": "rsi_above_exit", "rsi_period": 14, "level": 60},
            {"type": "time_stop", "max_bars": 30},
        ],
        "sizer": {"type": "fixed_fraction", "fraction": 0.2},
        "primary_tf": "D", "higher_tfs": [],
        "tags": ["mean_reversion"],
        "source": "유튜브 'RSI 지표를 활용한 핵심 매매법' (youtube.com/watch?v=WlUSq19j1Rk) 자막 분석 — RSI-시그널 골든크로스(시그널≤40) 진입, RSI60 익절. 원전은 크립토 15분봉 → 일봉 근사",
    },
    # ------------------------------------------------------------------
    # 유튜브 조사 2차 (2026-07-27)
    # ------------------------------------------------------------------
    "ichimoku_cloud_bounce": {
        "entry": {"type": "ichimoku_bounce", "tenkan": 9, "kijun": 26, "senkou": 52, "body_mult": 1.5},
        "filters": [],
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 5.0, "take_pct": 99.0},
            {"type": "ichimoku_exit"},
            {"type": "time_stop", "max_bars": 40},
        ],
        "sizer": {"type": "fixed_fraction", "fraction": 0.2},
        "primary_tf": "D", "higher_tfs": [],
        "tags": ["trend_follow", "support_bounce"],
        "source": "유튜브 '일목균형표 단타매매법' (youtube.com/watch?v=jE54FTenWsw) 자막 분석 — 양운 터치+장대양봉 반등. 원전 1시간봉→일봉 근사, '장대' 기준(평균 몸통 1.5배)은 자체 정의",
    },
    "accum_box_breakout": {
        "entry": {"type": "box_breakout", "box_period": 40, "max_box_range_pct": 15.0, "vol_mult": 2.5},
        "filters": [{"type": "ma_compare", "fast": 60, "slow": 120}],  # 역배열 매집 배제 (영상 필터)
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 5.0, "take_pct": 99.0},
            {"type": "atr_trailing", "period": 14, "mult": 3.0},
            {"type": "time_stop", "max_bars": 60},
        ],
        "sizer": {"type": "atr_risk", "risk_pct": 1.0},
        "primary_tf": "D", "higher_tfs": [],
        "tags": ["breakout", "volume", "accumulation"],
        "source": "유튜브 '세력 거래량 보는법' (youtube.com/watch?v=2fndu2K7Tv0) 자막 분석 — 저변동 박스+거래량 위축 후 대량거래 돌파. 박스폭 15%/40봉/거래량 2.5배는 자체 정의 (영상 미제시)",
    },
    "staggered_breakout": {
        "entry": {"type": "breakout", "lookback": 60},
        "filters": [
            {"type": "ma_compare", "fast": 60, "slow": 120},
            {"type": "volume", "period": 20, "min_ratio": 1.5},
        ],
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 6.0, "take_pct": 99.0},
            {"type": "atr_trailing", "period": 14, "mult": 3.0},
        ],
        "sizer": {"type": "atr_risk", "risk_pct": 1.0},
        "primary_tf": "D", "higher_tfs": [],
        "tags": ["trend_follow", "breakout"],
        "source": "유튜브 2fndu2K7Tv0의 '시간차 돌파' — 60일선>120일선 골든크로스 + 전고점(60봉) 돌파 + 거래량 동반. 영상이 '세 방식 중 신뢰도 최고'라 주장한 유일한 기계화 가능형",
    },
    # ------------------------------------------------------------------
    # 문헌 조사 2차 (2026-07-27) — 기존 풀에 없는 유형 위주
    # ------------------------------------------------------------------
    "double_seven": {
        "entry": {"type": "n_day_low", "lookback": 7},
        "filters": [{"type": "price_above_ma", "period": 200}],
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 8.0, "take_pct": 99.0},
            {"type": "n_day_high_exit", "lookback": 7},
            {"type": "time_stop", "max_bars": 20},
        ],
        "sizer": {"type": "fixed_fraction", "fraction": 0.2},
        "primary_tf": "D", "higher_tfs": [],
        "tags": ["mean_reversion"],
        "source": "Connors & Alvarez 'Double Seven' — 200일선 위 + 7일 최저 종가 매수 / 7일 최고 종가 매도 (원전은 무손절, 여기선 8% 안전벨트 추가)",
    },
    "ibs_reversion": {
        "entry": {"type": "ibs_below", "threshold": 0.2},
        "filters": [{"type": "price_above_ma", "period": 200}],
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 6.0, "take_pct": 99.0},
            {"type": "ibs_above_exit", "threshold": 0.8},
            {"type": "time_stop", "max_bars": 5},
        ],
        "sizer": {"type": "fixed_fraction", "fraction": 0.2},
        "primary_tf": "D", "higher_tfs": [],
        "tags": ["mean_reversion", "short_term"],
        "source": "Internal Bar Strength 평균회귀 (QuantifiedStrategies / Alvarez Quant Trading 문서화) — IBS<0.2 매수, IBS>0.8 청산",
    },
    "three_day_reversion": {
        "entry": {"type": "consecutive_down", "days": 3},
        "filters": [{"type": "price_above_ma", "period": 200}],
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 6.0, "take_pct": 99.0},
            {"type": "above_ma_exit", "period": 5},
            {"type": "time_stop", "max_bars": 10},
        ],
        "sizer": {"type": "fixed_fraction", "fraction": 0.2},
        "primary_tf": "D", "higher_tfs": [],
        "tags": ["mean_reversion"],
        "source": "Connors & Alvarez 'High Probability ETF Trading' (2009) 3-Day 평균회귀 — 3일 연속 고점·저점 하락 + 200일선 위 매수",
    },
    "minervini_breakout": {
        "entry": {"type": "breakout", "lookback": 50},
        "filters": [{"type": "minervini"}],
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 8.0, "take_pct": 99.0},
            {"type": "atr_trailing", "period": 14, "mult": 3.0},
        ],
        "sizer": {"type": "atr_risk", "risk_pct": 1.0},
        "primary_tf": "D", "higher_tfs": [],
        "tags": ["trend_follow", "breakout"],
        "source": "Mark Minervini 'Trade Like a Stock Market Wizard' (2013) 트렌드 템플릿(7조건, IBD RS 제외) + 50일 신고가 돌파 진입",
    },
    "clenow_momentum": {
        "entry": {"type": "ma_cross", "fast": 20, "slow": 50},
        "filters": [{"type": "clenow", "period": 90, "min_score": 40}],
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 8.0, "take_pct": 99.0},
            {"type": "atr_trailing", "period": 14, "mult": 3.5},
        ],
        "sizer": {"type": "atr_risk", "risk_pct": 1.0},
        "primary_tf": "D", "higher_tfs": [],
        "tags": ["momentum", "trend_follow"],
        "source": "Andreas Clenow 'Stocks on the Move' (2015) — 연율 지수회귀 기울기×R² 모멘텀 + 100일선/갭 제외 조건. 원전은 유니버스 순위 선별, 여기선 절대 임계값으로 근사",
    },
    # ------------------------------------------------------------------
    # 조사 4차 (2026-07-27) — 교과서 정통 조합 (기존 검증의 공백 메우기)
    # ------------------------------------------------------------------
    "bb_rsi_classic": {
        "entry": {"type": "bollinger_touch", "period": 20, "k": 2.0},
        "filters": [{"type": "rsi_range", "period": 14, "max_rsi": 35}],
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 4.0, "take_pct": 99.0},
            {"type": "bollinger_mid_exit", "period": 20},
            {"type": "time_stop", "max_bars": 15},
        ],
        "sizer": {"type": "fixed_fraction", "fraction": 0.2},
        "primary_tf": "D", "higher_tfs": [],
        "tags": ["mean_reversion", "confirmation"],
        "source": "볼린저+RSI 정통 조합 (교과서 표준): 하단 터치 반등 + RSI 과매도 동시 확인. 교과서는 RSI<30이나 반등 확인 시점엔 이미 RSI가 올라와 있어 35로 완화 (자체 판단, 명시)",
    },
    "ichimoku_tk": {
        "entry": {"type": "ichimoku_tk_cross"},
        "filters": [],
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 5.0, "take_pct": 99.0},
            {"type": "ichimoku_exit"},
            {"type": "time_stop", "max_bars": 40},
        ],
        "sizer": {"type": "fixed_fraction", "fraction": 0.2},
        "primary_tf": "D", "higher_tfs": [],
        "tags": ["trend_follow"],
        "source": "一目均衡表 정통 신호 — 전환선(9)이 기준선(26) 상향 돌파 (TK 크로스)",
    },
    "ichimoku_kumo": {
        "entry": {"type": "ichimoku_kumo_breakout"},
        "filters": [],
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 5.0, "take_pct": 99.0},
            {"type": "ichimoku_exit"},
            {"type": "atr_trailing", "period": 14, "mult": 3.0},
        ],
        "sizer": {"type": "atr_risk", "risk_pct": 1.0},
        "primary_tf": "D", "higher_tfs": [],
        "tags": ["trend_follow", "breakout"],
        "source": "一目均衡表 정통 신호 — 가격의 구름(Kumo) 상향 완전 돌파",
    },
    "ichimoku_sanyaku": {
        "entry": {"type": "ichimoku_tk_cross"},
        "filters": [
            {"type": "above_cloud"},
            {"type": "chikou", "lag": 26},
        ],
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 5.0, "take_pct": 99.0},
            {"type": "ichimoku_exit"},
            {"type": "atr_trailing", "period": 14, "mult": 3.0},
        ],
        "sizer": {"type": "atr_risk", "risk_pct": 1.0},
        "primary_tf": "D", "higher_tfs": [],
        "tags": ["trend_follow", "confirmation"],
        "source": "一目均衡表 삼역호전(三役好転) — 일목 이론 최강 매수 신호: TK크로스 + 가격이 구름 위 + 후행스팬이 26봉 전 가격 위, 3조건 동시 충족",
    },
    # ------------------------------------------------------------------
    # 코인 전용 (2026-07-27) — 분봉 데이터 확보로 구현 가능해진 장중 전략
    # ------------------------------------------------------------------
    "vol_breakout_05": {
        "entry": {"type": "volatility_breakout", "k": 0.5},
        "filters": [],
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 3.0, "take_pct": 99.0},
            {"type": "new_day_exit"},
        ],
        "sizer": {"type": "fixed_fraction", "fraction": 0.2},
        "primary_tf": "60m", "higher_tfs": ["D"],
        "tags": ["breakout", "intraday", "crypto"],
        "source": "Larry Williams 변동성 돌파 (1970s) — 목표가 = 당일시가 + 0.5×전일변동폭, 당일 청산. 코인 커뮤니티 표준 전략",
    },
    "vol_breakout_03": {
        "entry": {"type": "volatility_breakout", "k": 0.3},
        "filters": [],
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 3.0, "take_pct": 99.0},
            {"type": "new_day_exit"},
        ],
        "sizer": {"type": "fixed_fraction", "fraction": 0.2},
        "primary_tf": "60m", "higher_tfs": ["D"],
        "tags": ["breakout", "intraday", "crypto"],
        "source": "변동성 돌파 K=0.3 변형 (민감도 비교용)",
    },
    "vol_breakout_ma": {
        "entry": {"type": "volatility_breakout", "k": 0.5},
        "filters": [{"type": "price_above_ma", "period": 120}],  # 상승 국면에서만
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 3.0, "take_pct": 99.0},
            {"type": "new_day_exit"},
        ],
        "sizer": {"type": "fixed_fraction", "fraction": 0.2},
        "primary_tf": "60m", "higher_tfs": ["D"],
        "tags": ["breakout", "intraday", "crypto"],
        "source": "변동성 돌파 + 장기MA 필터 (하락장 진입 차단). 원전엔 없는 자체 조합",
    },
    "macd_zero_mtf": {
        "entry": {"type": "macd_cross", "zero_line": True},
        "filters": [{"type": "higher_tf_trend", "tf": "W", "ma_period": 10}],
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 5.0, "take_pct": 99.0},
            {"type": "atr_trailing", "period": 14, "mult": 3.0},
        ],
        "sizer": {"type": "atr_risk", "risk_pct": 1.0},
        "primary_tf": "D", "higher_tfs": ["W"],
        "tags": ["trend_follow", "mtf"],
        "source": "macd_trend_mtf + 제로라인 필터 — Trading Rush 100회 실측(62% vs 53%, youtube.com/watch?v=nmffSjdZbWQ) 근거의 개선 가설",
    },
    "double_rsi": {
        "entry": {"type": "double_rsi_cross", "fast": 7, "slow": 21},
        "filters": [],
        "exits": [
            {"type": "fixed_stop_take", "stop_pct": 4.0, "take_pct": 99.0},
            {"type": "double_rsi_exit", "fast": 7, "slow": 21},
        ],
        "sizer": {"type": "fixed_fraction", "fraction": 0.2},
        "primary_tf": "D", "higher_tfs": [],
        "tags": ["trend_follow", "crypto"],
        "source": "유튜브 '어느 미친 수학자가 만든 RSI 단타 매매법' (youtube.com/watch?v=N6ItrRIlpeI) — RSI(7)/RSI(21) 크로스. 같은 영상의 '타오 RSI' 계열 2종은 비공개 지표라 제외",
    },
    "turtle_20_10_atr": {
        "entry": {"type": "breakout", "lookback": 20},
        "filters": [],
        "exits": [
            {"type": "atr_stop", "period": 20, "mult": 2.0},   # ★ 원전의 2N 손절
            {"type": "donchian_exit", "lookback": 10},
        ],
        "sizer": {"type": "atr_risk", "risk_pct": 1.0, "atr_period": 20, "stop_mult": 2.0},
        "primary_tf": "D", "higher_tfs": [],
        "tags": ["trend_follow", "breakout"],
        "source": "터틀 System 1 원전 충실판 — 20일 돌파 진입 / 손절 = 진입가-2N(ATR20×2) / 10일 저점 청산 / 2N 리스크 사이징. 기존 turtle_20_10은 손절을 고정 6%로 대체한 변형(비교군)",
    },
}


def build_preset(name: str) -> CompositeStrategy:
    if name not in PRESETS:
        raise ValueError(f"미등록 프리셋: {name} (가능: {list(PRESETS)})")
    return build_strategy(name, PRESETS[name])


def preset_meta(name: str) -> dict:
    cfg = PRESETS[name]
    return {
        "primary_tf": cfg.get("primary_tf", "D"),
        "higher_tfs": cfg.get("higher_tfs", []),
        "tags": cfg.get("tags", []),
    }
