# VN Gold Model Card

## Scope

This model card documents the rebuilt VN gold decision-support pipeline as of snapshot `2026-07-11`. The target is calendar-month net return after spread: buy at current SJC sell price and exit at the nearest available SJC buy price on or after `date + 1/3/5 months`.

## Data And Targets

- Model frame rows: 5,485, from `2011-07-06` to `2026-07-11`.
- Premium missing rate: 0.0% after rebuilding global gold conversion with `USD/oz * USD/VND * 37.5 / 31.1034768`.
- Target non-null counts: {'net_return_1m': 5455, 'net_return_3m': 5394, 'net_return_5m': 5335}.
- Deposit-rate feature: `excluded_no_historical_asof_rate`; historical opportunity-cost benchmark remains excluded unless verified deposit history is available.

## Point Model Leaderboard

| Horizon | Best MAE model | MAE | RMSE | Best DA model | Directional accuracy |
|---|---:|---:|---:|---:|---:|
| 1 th?ng | historical_median_return | 0.0117 | 0.0188 | historical_mean_return | 71.0% |
| 3 th?ng | historical_mean_return | 0.0310 | 0.0402 | historical_mean_return | 97.5% |
| 5 th?ng | historical_mean_return | 0.0653 | 0.0830 | ridge | 98.4% |

## Quantile/Downside Models

| Horizon | Best quantile model | Phase | Pinball loss |
|---|---:|---:|---:|
| 1 th?ng | sklearn_gbr_q05 | validation | 0.0021 |
| 3 th?ng | sklearn_gbr_q05 | validation | 0.0041 |
| 5 th?ng | sklearn_gbr_q05 | validation | 0.0053 |

## Decision Rule Backtest

Default decision rule: `P(return > 0) >= 0.50` and `q10 >= -10%`.

| Horizon | Phase | Signal days | Observations | Signal rate | Avg buy-day return | Avg strategy return |
|---|---:|---:|---:|---:|---:|---:|
| 1 th?ng | test | 32 | 365 | 8.8% | 1.34% | 0.12% |
| 1 th?ng | validation | 0 | 365 | 0.0% | n/a | 0.00% |
| 3 th?ng | test | 328 | 466 | 70.4% | 9.87% | 6.95% |
| 3 th?ng | validation | 306 | 731 | 41.9% | 1.46% | 0.61% |
| 5 th?ng | test | 407 | 407 | 100.0% | 19.95% | 19.95% |
| 5 th?ng | validation | 366 | 731 | 50.1% | 7.05% | 3.53% |

## Snapshot Forecast

| Horizon | Expected return | Q10 downside | P(return > 0) | Decision |
|---|---:|---:|---:|---:|
| 1 th?ng | -5.17% | -6.85% | 0.73% | no_buy |
| 3 th?ng | 2.77% | -8.02% | 91.09% | buy |
| 5 th?ng | 9.65% | -3.84% | 100.00% | buy |

## Known Caveats

- News features are still research-event-date lagged; strict realtime availability is not fully proven.
- Retail deposit rates are forward-monitoring only and are not used as historical opportunity cost.
- VECM was screened but not promoted to forecast because the rolling cointegration screen did not pass.
- DeepAR/TFT dependencies are installed, but no deep-learning runner is promoted in this tabular/econometric pipeline yet.
