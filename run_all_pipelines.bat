@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d "C:\Users\admin\Documents\Lab Workplace\vn-gold-market-analysis"

echo ===== STEP 1: Premium Decomposition =====
python scripts/pipeline/build_premium_decomposition.py --from 2010-01-01 --to 2026-07-07 --out-dir data/lake/enriched
echo STEP 1 DONE: %ERRORLEVEL%
echo.

echo ===== STEP 2: Event Panel =====
python scripts/pipeline/build_event_panel.py --from 2010-01-01 --to 2027-12-31 --out-dir data/lake/enriched
echo STEP 2 DONE: %ERRORLEVEL%
echo.

echo ===== STEP 3: Enhanced Features =====
python scripts/pipeline/collect_enhanced_features.py --from 2010-01-01 --to 2026-07-07 --out-dir data/lake/external_features_v2
echo STEP 3 DONE: %ERRORLEVEL%
echo.

echo ===== ALL PIPELINE STEPS COMPLETE =====
pause
