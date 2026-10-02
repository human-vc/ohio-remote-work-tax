#!/bin/sh
set -e
PY=${PY:-.venv/bin/python}
M=scripts/revenue/model.py
L=output/logs
mkdir -p output/revenue $L
for s in sample sample_controls potential summary soi_wages soi_wages_earnings lodes_place bedroom preperiod_sample altnorm sample_aos sample_nocredit matched_pairs sd_overlap sd_income_panel sd_income; do
  $PY scripts/revenue/$s.py > $L/revenue_$s.log 2>&1
done
OUT_TAG=main SAVE_VCV=1 $PY $M 1999 > $L/model_main.log 2>&1
OUT_TAG=nocontrols NO_CONTROLS=1 $PY $M 1999 > $L/model_nocontrols.log 2>&1
OUT_TAG=aos SAMPLE=output/revenue/sample_aos.csv AOS_OUTCOME=output/revenue/aos_outcome.csv $PY $M 1999 > $L/model_aos.log 2>&1
OUT_TAG=drop5 EXCLUDE_COL=stplc EXCLUDE_VAL=$($PY scripts/revenue/extreme_loss.py) $PY $M 1999 > $L/model_drop5.log 2>&1
OUT_TAG=credit_factor SAMPLE=output/revenue/sample_with_potential.csv ADD_POTENTIAL=1 $PY $M 1999 > $L/model_credit_factor.log 2>&1
OUT_TAG=nocredit_pooled SAMPLE=output/revenue/sample_nocredit_extended.csv ADD_POTENTIAL=1 $PY $M 999 > $L/model_nocredit_pooled.log 2>&1
OUT_TAG=nocredit_zero SAMPLE=output/revenue/sample_nocredit_zero.csv $PY $M 999 > $L/model_nocredit_zero.log 2>&1
for m in coll wage ratio; do
  OUT_TAG=soi85_$m SOI_RATIO=1 SOI_MODE=$m PURITY=0.30 YEAR_END=2022 POST_YEARS=2022 CONTRAST=2022-2021 $PY $M 1999 > $L/model_soi85_$m.log 2>&1
done
OUT_TAG=soi_all_ratio SOI_RATIO=1 PURITY=0 YEAR_END=2022 POST_YEARS=2022 $PY $M 1999 > $L/model_soi_all_ratio.log 2>&1
OUT_TAG=soi_earnw_ratio SOI_RATIO=1 PURITY=0.30 SOI_FILE=output/revenue/soi_place_wages_earnw.csv YEAR_END=2022 POST_YEARS=2022 $PY $M 1999 > $L/model_soi_earnw_ratio.log 2>&1
OUT_TAG=soi70_ratio SOI_RATIO=1 PURITY=0.70 YEAR_END=2022 POST_YEARS=2022 $PY $M 1999 > $L/model_soi70_ratio.log 2>&1
OUT_TAG=soi_bedroom_ratio SOI_RATIO=1 SOI_MODE=ratio PURITY=0.30 KEEP_FILE=output/revenue/bedroom_purityge030.csv KEEP_VAL=1 YEAR_END=2022 POST_YEARS=2022 $PY $M 1999 > $L/model_soi_bedroom_ratio.log 2>&1
OUT_TAG=sd_agency SOI_RATIO=1 SOI_MODE=wage SOI_FILE=output/revenue/sd_fagi_as_wages.csv $PY $M 999 > $L/model_sd_agency.log 2>&1
OUT_TAG=sd_aos SAMPLE=output/revenue/sample_aos.csv SOI_RATIO=1 SOI_MODE=wage SOI_FILE=output/revenue/sd_fagi_as_wages.csv $PY $M 999 > $L/model_sd_aos.log 2>&1
OUT_TAG=common_agency SAMPLE=output/revenue/sample_common.csv $PY $M 1999 > $L/model_common_agency.log 2>&1
OUT_TAG=common_aos SAMPLE=output/revenue/sample_common.csv AOS_OUTCOME=output/revenue/aos_outcome.csv $PY $M 1999 > $L/model_common_aos.log 2>&1
OUT_TAG=common_diff SAMPLE=output/revenue/sample_common.csv AOS_OUTCOME=output/revenue/aos_outcome.csv AOS_MINUS_RITA=1 $PY $M 1999 > $L/model_common_diff.log 2>&1
OUT_TAG=withholding COMPONENT=withholding $PY $M 1999 > $L/model_withholding.log 2>&1
OUT_TAG=p85_2016 SAVE_VCV=1 SAMPLE=output/revenue/sample_preperiod_2012.csv $PY $M 1999 > $L/model_p85_2016.log 2>&1
OUT_TAG=p85_2012 SAVE_VCV=1 SAMPLE=output/revenue/sample_preperiod_2012.csv YEAR_START=2012 COLLECTIONS=output/revenue/rita_member_collections_2006_2025.csv $PY $M 1999 > $L/model_p85_2012.log 2>&1
OUT_TAG=altnorm_121 SAMPLE=output/revenue/sample_altnorm_121.csv $PY $M 1999 > $L/model_altnorm_121.log 2>&1
OUT_TAG=altnorm_85_2012 SAMPLE=output/revenue/sample_altnorm_85.csv YEAR_START=2012 COLLECTIONS=output/revenue/rita_member_collections_2006_2025.csv $PY $M 1999 > $L/model_altnorm_85_2012.log 2>&1
$PY scripts/revenue/mdr_components.py > $L/revenue_mdr_components.log 2>&1
for c in total withholding wh_tax individual net_profit; do
  OUT_TAG=mdr_$c YEAR_START=2017 COMPONENT=$c COMPONENT_FILE=output/revenue/components_mdr.csv $PY $M 999 > $L/model_mdr_$c.log 2>&1
done
for c in total_s wh_s ind_s np_s; do
  OUT_TAG=mdr_$c NOLOG=1 YEAR_START=2017 COMPONENT=$c COMPONENT_FILE=output/revenue/components_mdr.csv $PY $M 999 > $L/model_mdr_$c.log 2>&1
done
OUT_TAG=mdr_cf_withholding SAMPLE=output/revenue/sample_with_potential.csv ADD_POTENTIAL=1 YEAR_START=2017 COMPONENT=withholding COMPONENT_FILE=output/revenue/components_mdr.csv $PY $M 999 > $L/model_mdr_cf_withholding.log 2>&1
for c in withholding individual; do
  OUT_TAG=mdr_nc_$c SAMPLE=output/revenue/sample_nocredit_zero.csv YEAR_START=2017 COMPONENT=$c COMPONENT_FILE=output/revenue/components_mdr.csv $PY $M 999 > $L/model_mdr_nc_$c.log 2>&1
done
$PY scripts/revenue/leave_one_out.py > $L/revenue_leave_one_out.log 2>&1
if command -v Rscript >/dev/null 2>&1; then
  Rscript scripts/revenue/honestdid.R > $L/revenue_honestdid.log 2>&1
else
  echo "Rscript not found: skipping scripts/revenue/honestdid.R"
fi
