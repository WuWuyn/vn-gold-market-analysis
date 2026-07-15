# Full Data Quality Audit - VN Gold Market Analysis

Generated at: 2026-07-15T21:14:58.034525+00:00

## Executive Verdict

The current lake is **not decision-safe** for investment conclusions until the critical issues below are fixed and all downstream artifacts are rebuilt.

## Findings

| Severity | Check | Status | Evidence | Impacted artifacts | Recommended fix |
|---|---|---|---|---|---|
| high | mixed_or_duplicate_daily_grain | failed | pipeline_output_domestic_daily.csv: 106,008 duplicate date rows if interpreted as one-row-per-day. This table appears to be mixed source/product grain and must not be used as a daily model frame without a wider key or aggregation. | pipeline_output_domestic_daily.csv | Declare the canonical grain, aggregate to one row per date before modeling, and reserve source/product rows for audit only. |
| high | negative_spread | failed | gold_quotes_sjc_historical.csv: 1 rows have sell < buy for buy/sell. | gold_quotes_sjc_historical.csv | Inspect source/unit mapping and exclude invalid target rows from model training. |
| high | negative_spread | failed | pipeline_output_domestic_daily.csv: 1,544 rows have sell < buy for buy_price/sell_price. | pipeline_output_domestic_daily.csv | Inspect source/unit mapping and exclude invalid target rows from model training. |
| high | news_realtime_availability | warning | Only 14.24% of news rows are strict_realtime_verified; most rows are backfilled. | news features; event_regime; model_frame_daily; model interpretation | Exclude backfilled news from decision/paper-trading features or run sensitivity with strict-only mode. |
| medium | deposit_history_coverage | warning | Retail deposit rates are forward_monitoring_only; they cannot benchmark historical 2011-2026 model returns. | deposit_return_* features; opportunity cost comparison | Do not include deposit excess-return claims in historical backtests until verified historical deposit data exists. |
| medium | duplicate_named_artifact_drift | warning | global_reference_daily.csv: 2 copies with 2 different hashes. | global_reference_daily.csv; enriched\master\normalized\global_reference_daily.csv | Declare canonical artifact paths and stop reading ambiguous duplicate filenames. |
| medium | duplicate_named_artifact_drift | warning | gold_daily_enriched.csv: 2 copies with 2 different hashes. | gold_daily_enriched.csv; gold_prices\gold_daily_enriched.csv | Declare canonical artifact paths and stop reading ambiguous duplicate filenames. |
| medium | duplicate_named_artifact_drift | warning | gold_quotes_sjc_historical.csv: 2 copies with 2 different hashes. | gold_quotes_sjc_historical.csv; domestic_target\gold_quotes_sjc_historical.csv | Declare canonical artifact paths and stop reading ambiguous duplicate filenames. |
| medium | duplicate_named_artifact_drift | warning | vn_macro_asof_panel.csv: 2 copies with 2 different hashes. | vn_macro_asof_panel.csv; enriched\master\normalized\vn_macro_asof_panel.csv | Declare canonical artifact paths and stop reading ambiguous duplicate filenames. |
| medium | sbv_deposit_rate_source | passed_with_caveat | SBV structure 137473 is classified as central_fx, not deposit_rate. No verified SBV deposit history source is present. | deposit opportunity cost features; report caveats | Keep SBV 137473 as official central FX only; use verified deposit-rate source or forward monitoring for retail rates. |

## Core Dataset Profiles

| Path | Rows | Cols | Date spans | Duplicate rows |
|---|---:|---:|---|---:|
| gold_quotes_sjc_historical.csv | 28230 | 13 | {"business_date": {"min": "2011-07-06", "max": "2026-07-11", "non_null": 28230}, "date": {"min": "2011-07-06", "max": "2026-07-11", "non_null": 28230}} | 7 |
| pipeline_output_domestic_daily.csv | 111942 | 18 | {"business_date": {"min": "2010-01-02", "max": "2026-07-11", "non_null": 111942}, "date": {"min": "2010-01-02", "max": "2026-07-11", "non_null": 111942}} | 20038 |
| pipeline_output_global_reference.csv | 3914 | 9 | {"date": {"min": "2011-07-06", "max": "2026-07-10", "non_null": 3914}} | 0 |
| pipeline_output_premium_enriched.csv | 5485 | 24 | {"date": {"min": "2011-07-06", "max": "2026-07-11", "non_null": 5485}} | 0 |
| pipeline_output_vn_macro_asof.csv | 36705 | 10 | {"available_from": {"min": "2010-01-01", "max": "2026-07-11", "non_null": 5865}} | 0 |
| pipeline_output_event_regime.csv | 1850 | 13 | {"event_date": {"min": "2010-04-15", "max": "2027-10-05", "non_null": 1850}} | 0 |
| modeling/model_frame_daily.csv | 5485 | 783 | {"date": {"min": "2011-07-06", "max": "2026-07-11", "non_null": 5485}} | 0 |
| modeling/snapshot_forecasts.csv | 3 | 13 | {} | 0 |
| modeling/decision_signals.csv | 27585 | 15 | {"date": {"min": "2023-01-01", "max": "2026-04-11", "non_null": 27585}} | 0 |
| modeling/walk_forward_predictions.csv | 56085 | 8 | {"date": {"min": "2023-01-01", "max": "2026-06-11", "non_null": 56085}} | 0 |
| modeling/paper_trading_ledger.csv | 3 | 21 | {"feature_date": {"min": "2026-07-11", "max": "2026-07-11", "non_null": 3}, "signal_date": {"min": "2026-07-11", "max": "2026-07-11", "non_null": 3}} | 0 |
| news_availability_audit.csv | 3441 | 17 | {"event_date": {"min": "2010-11-01", "max": "2026-07-11", "non_null": 3441}, "published_at": {"min": "2010-11-01", "max": "2026-07-11", "non_null": 3441}} | 0 |
| source_discovery/sbv_structures.csv | 15 | 18 | {} | 0 |
| events/sbv_gold_policy_events.csv | 3 | 10 | {"event_date": {"min": "2026-07-16", "max": "2026-07-16", "non_null": 3}, "published_at": {"min": "2026-07-16", "max": "2026-07-16", "non_null": 3}} | 0 |
| normalized/retail_deposit_rates.csv | 15 | 13 | {"date": {"min": "2026-07-16", "max": "2026-07-16", "non_null": 15}, "published_at": {"min": "2026-07-16", "max": "2026-07-16", "non_null": 15}, "available_from": {"min": "2026-07-16", "max": "2026-07-16", "non_null": 15}} | 0 |
| normalized/sbv_policy_rates.csv | 0 | 11 | {} | 0 |
| normalized/lbma_gold_spot_am_pm.csv | 7 | 10 | {"date": {"min": "2026-07-16", "max": "2026-07-16", "non_null": 7}, "available_from": {"min": "2026-07-16", "max": "2026-07-16", "non_null": 7}} | 0 |

## Check Details

```json
{
  "unit_conversion": {
    "correct_oz_per_luong": 1.2056529963235494,
    "wrong_luong_per_oz_constant": 0.6883203717842323,
    "wrong_over_correct_factor_expected": 1.205,
    "pipeline_output_premium_enriched.csv": {
      "rows_checked": 5485,
      "stored_to_correct_median": 1.000000000001008,
      "stored_to_correct_p05": 0.9999999998759195,
      "stored_to_correct_p95": 1.000000000123291,
      "current_premium_pct_median": 0.102069,
      "correct_premium_pct_median": 0.10206913559249957,
      "correct_positive_premium_share": 0.9562443026435734
    },
    "modeling/model_frame_daily.csv": {
      "rows_checked": 5485,
      "stored_to_correct_median": 1.000000000001008,
      "stored_to_correct_p05": 0.9999999998759195,
      "stored_to_correct_p95": 1.000000000123291,
      "current_premium_pct_median": 0.102069,
      "correct_premium_pct_median": 0.10189028409366667,
      "correct_positive_premium_share": 0.9615314494074749
    }
  },
  "horizon_semantics": {
    "date_min": "2011-07-06",
    "date_max": "2026-07-11",
    "unique_dates": 5485,
    "calendar_days": 5485,
    "missing_calendar_days": 0,
    "diff_counts": {
      "1.0": 5484
    },
    "horizon_1m": {
      "non_null_targets": 5455,
      "exit_after_target_violations": 0,
      "exit_lag_days_median": 0.0,
      "exit_lag_days_max": 0.0
    },
    "horizon_3m": {
      "non_null_targets": 5394,
      "exit_after_target_violations": 0,
      "exit_lag_days_median": 0.0,
      "exit_lag_days_max": 0.0
    },
    "horizon_5m": {
      "non_null_targets": 5335,
      "exit_after_target_violations": 0,
      "exit_lag_days_median": 0.0,
      "exit_lag_days_max": 0.0
    }
  },
  "grain_and_validity": {
    "gold_quotes_sjc_historical.csv": {
      "rows": 28230,
      "cols": 13,
      "exact_duplicate_rows": 7,
      "date_col": "date",
      "date_min": "2011-07-06",
      "date_max": "2026-07-11",
      "buy_sell_negative_spread_rows": 1,
      "buy_sell_non_positive_rows": 1
    },
    "pipeline_output_domestic_daily.csv": {
      "rows": 111942,
      "cols": 18,
      "exact_duplicate_rows": 20038,
      "date_col": "date",
      "date_min": "2010-01-02",
      "date_max": "2026-07-11",
      "duplicate_date_rows": 106008,
      "buy_price_sell_price_negative_spread_rows": 1544,
      "buy_price_sell_price_non_positive_rows": 11
    },
    "pipeline_output_global_reference.csv": {
      "rows": 3914,
      "cols": 9,
      "exact_duplicate_rows": 0,
      "date_col": "date",
      "date_min": "2011-07-06",
      "date_max": "2026-07-10",
      "duplicate_date_rows": 0
    },
    "pipeline_output_premium_enriched.csv": {
      "rows": 5485,
      "cols": 24,
      "exact_duplicate_rows": 0,
      "date_col": "date",
      "date_min": "2011-07-06",
      "date_max": "2026-07-11",
      "duplicate_date_rows": 0,
      "buy_consensus_sell_consensus_negative_spread_rows": 0,
      "buy_consensus_sell_consensus_non_positive_rows": 0
    },
    "pipeline_output_vn_macro_asof.csv": {
      "rows": 36705,
      "cols": 10,
      "exact_duplicate_rows": 0
    },
    "pipeline_output_event_regime.csv": {
      "rows": 1850,
      "cols": 13,
      "exact_duplicate_rows": 0,
      "date_col": "event_date",
      "date_min": "2010-04-15",
      "date_max": "2027-10-05"
    },
    "modeling/model_frame_daily.csv": {
      "rows": 5485,
      "cols": 783,
      "exact_duplicate_rows": 0,
      "date_col": "date",
      "date_min": "2011-07-06",
      "date_max": "2026-07-11",
      "duplicate_date_rows": 0,
      "buy_price_sell_price_negative_spread_rows": 0,
      "buy_price_sell_price_non_positive_rows": 0
    },
    "modeling/snapshot_forecasts.csv": {
      "rows": 3,
      "cols": 13,
      "exact_duplicate_rows": 0
    },
    "modeling/decision_signals.csv": {
      "rows": 27585,
      "cols": 15,
      "exact_duplicate_rows": 0,
      "date_col": "date",
      "date_min": "2023-01-01",
      "date_max": "2026-04-11"
    },
    "modeling/walk_forward_predictions.csv": {
      "rows": 56085,
      "cols": 8,
      "exact_duplicate_rows": 0,
      "date_col": "date",
      "date_min": "2023-01-01",
      "date_max": "2026-06-11"
    },
    "modeling/paper_trading_ledger.csv": {
      "rows": 3,
      "cols": 21,
      "exact_duplicate_rows": 0,
      "date_col": "feature_date",
      "date_min": "2026-07-11",
      "date_max": "2026-07-11"
    },
    "news_availability_audit.csv": {
      "rows": 3441,
      "cols": 17,
      "exact_duplicate_rows": 0,
      "date_col": "event_date",
      "date_min": "2010-11-01",
      "date_max": "2026-07-11"
    },
    "source_discovery/sbv_structures.csv": {
      "rows": 15,
      "cols": 18,
      "exact_duplicate_rows": 0
    },
    "events/sbv_gold_policy_events.csv": {
      "rows": 3,
      "cols": 10,
      "exact_duplicate_rows": 0,
      "date_col": "event_date",
      "date_min": "2026-07-16",
      "date_max": "2026-07-16"
    },
    "normalized/retail_deposit_rates.csv": {
      "rows": 15,
      "cols": 13,
      "exact_duplicate_rows": 0,
      "date_col": "date",
      "date_min": "2026-07-16",
      "date_max": "2026-07-16"
    },
    "normalized/sbv_policy_rates.csv": {
      "exists_or_rows": false
    },
    "normalized/lbma_gold_spot_am_pm.csv": {
      "rows": 7,
      "cols": 10,
      "exact_duplicate_rows": 0,
      "date_col": "date",
      "date_min": "2026-07-16",
      "date_max": "2026-07-16"
    }
  },
  "asof_leakage": {
    "global_feature_date": {
      "valid_rows": 5484,
      "violations": 0,
      "rule": "global_feature_date <= date-1"
    },
    "gpr_feature_date": {
      "valid_rows": 5485,
      "violations": 0,
      "rule": "gpr_feature_date <= date"
    },
    "macro_feature_date": {
      "valid_rows": 5485,
      "violations": 0,
      "rule": "macro_feature_date <= date"
    },
    "news_strict_realtime_verified_share": 0.14240046498111014
  },
  "source_semantics": {
    "sbv_structure_classification_counts": {
      "gold_policy_candidate": 11,
      "unknown": 3,
      "central_fx": 1
    },
    "sbv_137473": [
      {
        "generated_at": "2026-07-15T17:02:34.056031+00:00",
        "content_structure_id": 137473,
        "classification": "central_fx",
        "classification_note": "verified: fields match SBV central USD/VND rate",
        "http_status": 200,
        "row_count_sample": 10,
        "date_min_sample": "2026-07-03",
        "date_max_sample": "2026-07-15",
        "field_names": "ChuThich|NgayBanHanh|NgayBatDau|NgayKetThuc|SoVanBan|TyGiaChu|TyGiaSo",
        "title_samples": "15/07/2026 || 14/07/2026 || 13/07/2026 || 11/07/2026 || 10/07/2026",
        "source_url_samples": "15/07/2026 || 14/07/2026 || 13/07/2026 || 11/07/2026 || 10/07/2026",
        "seed_hits": "https://sbv.gov.vn/vi/ :: Trang Chủ - Ngân hàng Nhà nước Việt Nam || https://sbv.gov.vn/vi/bieu-do-ty-gia-trung-tam :: Tỷ giá trung tâm - Ngân hàng Nhà nước Việt Nam || https://sbv.gov.vn/vi/quan-ly-hoat-dong-ngoai-hoi-va-hoat-dong-kinh-doanh-vang :: Quản lý hoạt động ngoại hối và hoạt động kinh doanh vàng - Ngân hàng Nhà nước Việt Nam",
        "endpoint_url": "https://sbv.gov.vn/vi/o/headless-delivery/v1.0/content-structures/137473/structured-contents?pageSize=10&sort=datePublished:desc",
        "raw_hash": "828392abb8f710b2badf02414f58376d21bbc3f92824d7ee8b0c37d91fb5945f",
        "is_central_fx": true,
        "is_interest_rate_candidate": false,
        "is_gold_policy_candidate": false,
        "sample_fields_json": "[{\"NgayBatDau\": \"2026-07-14T17:00:00Z\", \"NgayKetThuc\": \"2026-07-14T17:00:00Z\", \"ChuThich\": \"\", \"TyGiaSo\": \"25233\", \"TyGiaChu\": \"Hai mươi lăm nghìn hai trăm ba mươi ba Đồng Việt Nam\", \"SoVanBan\": \"283/TB-NHNN\", \"NgayBanHanh\": \"2026-07-14T17:00:00Z\"}, {\"NgayBatDau\": \"2026-07-13T17:00:00Z\", \"NgayKetThuc\": \"2026-07-13T17:00:00Z\", \"ChuThich\": \"\", \"TyGiaSo\": \"25225\", \"TyGiaChu\": \"Hai mươi lăm nghìn hai trăm hai mươi lăm Đồng Việt Nam\", \"SoVanBan\": \"280/TB-NHNN\", \"NgayBanHanh\": \"2026-07-13T17:00:00Z\"}, {\"NgayBatDau\": \"2026-07-12T17:00:00Z\", \"NgayKetThuc\": \"2026-07-12T17:00:00Z\", \"ChuThich\": \"\", \"TyGiaSo\": \"25220\", \"TyGiaChu\": \"Hai mươi lăm nghìn hai trăm hai mươi Đồng Việt Nam\", \"SoVanBan\": \"277/TB-NHNN\", \"NgayBanHanh\": \"2026-07-12T17:00:00Z\"}]"
      }
    ],
    "retail_deposit_rows": 15,
    "retail_deposit_history_status_counts": {
      "forward_monitoring_only": 15
    }
  },
  "duplicate_copies": {
    "domestic_gold_quotes.csv": {
      "copies": {
        "domestic_gold_quotes.csv": "18d660555acd7430e91566fa8e93b6ede8a5a2559e5bf2929ebbd82720d3c6aa",
        "domestic_target\\domestic_gold_quotes.csv": "18d660555acd7430e91566fa8e93b6ede8a5a2559e5bf2929ebbd82720d3c6aa",
        "domestic_target\\normalized\\domestic_gold_quotes.csv": "18d660555acd7430e91566fa8e93b6ede8a5a2559e5bf2929ebbd82720d3c6aa"
      },
      "unique_hashes": 1
    },
    "event_regime_panel.csv": {
      "copies": {
        "event_regime_panel.csv": "ae2b4a9999baa103232f52a227691a15cc519caa30622c68208a337e5bef1e48",
        "enriched\\master\\normalized\\event_regime_panel.csv": "2f51d0b1d55507099ef60bb0e1f4fea195f248dd616e79649d4780a1c2f9dde0"
      },
      "unique_hashes": 2
    },
    "global_reference_daily.csv": {
      "copies": {
        "global_reference_daily.csv": "9e6e395731baf8cfb6df5e587a5f82cee782e0d6540dc4bd7868d030b1904591",
        "enriched\\master\\normalized\\global_reference_daily.csv": "a6524f9e70da8c57bfaf737d08325ce4ad49c115401f55fde399a8cbaa407b0a"
      },
      "unique_hashes": 2
    },
    "gold_daily_enriched.csv": {
      "copies": {
        "gold_daily_enriched.csv": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "gold_prices\\gold_daily_enriched.csv": "81bdf75f4f01b2d21cf47bc90d32b39f3421d89fb0046ec697f3e049bcbb5438"
      },
      "unique_hashes": 2
    },
    "gold_domestic_daily_panel.csv": {
      "copies": {
        "gold_domestic_daily_panel.csv": "f942e8825494350ce222a8fdf58058fd8590146eee00f440acc4be6314081179",
        "enriched\\master\\normalized\\gold_domestic_daily_panel.csv": "4baab296c0063605d5b7b0d86401f4a547e853a5bee2f8040f8381f31012f2f3"
      },
      "unique_hashes": 2
    },
    "gold_quotes_sjc_historical.csv": {
      "copies": {
        "gold_quotes_sjc_historical.csv": "6a6c6053db33e47086fb98fcf801e6d64d26bdce5807924fa44ca41e1443ccac",
        "domestic_target\\gold_quotes_sjc_historical.csv": "764d6f0a64fb0e2c8ee611168c73bafd53e3be542612770a26500319c0fdd8cd"
      },
      "unique_hashes": 2
    },
    "vn_macro_asof_panel.csv": {
      "copies": {
        "vn_macro_asof_panel.csv": "72fc861f7f3dce5f6f6fa687ad9d54420d0e3e0301b408e82ab4f8c8128e661c",
        "enriched\\master\\normalized\\vn_macro_asof_panel.csv": "827fa012203dde0193855df3cc1f9348f119dd2f9fa10c016df351352f59b29f"
      },
      "unique_hashes": 2
    }
  }
}
```
