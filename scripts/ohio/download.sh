#!/bin/sh
set -e
R=data/raw
mkdir -p $R/lodes $R/soi $R/baf $R/odt_y2 $R/ccd
get() { [ -s "$2" ] || curl -sfL --retry 3 -A "Mozilla/5.0" -o "$2" "$1"; }
L=https://lehd.ces.census.gov/data/lodes/LODES8/oh
for y in 2019 2023; do get $L/od/oh_od_main_JT00_$y.csv.gz $R/lodes/oh_od_main_JT00_$y.csv.gz; done
get $L/od/oh_od_aux_JT00_2019.csv.gz $R/lodes/oh_od_aux_JT00_2019.csv.gz
for y in 2015 2019 2023; do get $L/rac/oh_rac_S000_JT00_$y.csv.gz $R/lodes/oh_rac_S000_JT00_$y.csv.gz; done
get $L/wac/oh_wac_S000_JT00_2019.csv.gz $R/lodes/oh_wac_S000_JT00_2019.csv.gz
get $L/oh_xwalk.csv.gz $R/lodes/oh_xwalk.csv.gz
for y in 16 17 18 19 20 21 22; do
  [ -s $R/soi/oh_$y.csv ] || curl -sfL --retry 3 -A "Mozilla/5.0" "https://www.irs.gov/pub/irs-soi/${y}zpallagi.csv" | awk -F, 'NR==1 || $2=="OH" || $2=="\"OH\""' > $R/soi/oh_$y.csv
done
if [ ! -s $R/baf/BlockAssign_ST39_OH_SDUNI.txt ]; then
  get https://www2.census.gov/geo/docs/maps-data/data/baf2020/BlockAssign_ST39_OH.zip $R/baf/BlockAssign_ST39_OH.zip
  unzip -o -q $R/baf/BlockAssign_ST39_OH.zip BlockAssign_ST39_OH_SDUNI.txt BlockAssign_ST39_OH_INCPLACE_CDP.txt -d $R/baf
fi
Y=https://dam.assets.ohio.gov/raw/upload/tax.ohio.gov/tax_analysis/tax_data_series/individual_income/y2
for f in y2ty12.xls y2ty13.xls y2ty14.xls y2ty15.xlsx y2ty16.xlsx y2ty17.xls y2ty18.xls y2ty19.xlsx y2ty20.xlsx y2ty21.xlsx Y2_TY2022.xlsx Y2_TY2023.xlsx Y2_TY2024.xlsx; do get $Y/$f $R/odt_y2/$f; done
get "https://educationdata.urban.org/api/v1/school-districts/ccd/directory/2019/?fips=39" $R/ccd/urban_ccd_lea_oh_2019.json
