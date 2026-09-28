#!/bin/sh
set -e
mkdir -p data/raw/lodes data/raw/baf
get() { [ -f "$1" ] || curl -fL --retry 3 -o "$1" "$2"; }
get data/raw/lodes/ky_od_main_JT00_2019.csv.gz https://lehd.ces.census.gov/data/lodes/LODES8/ky/od/ky_od_main_JT00_2019.csv.gz
get data/raw/lodes/ky_wac_S000_JT00_2019.csv.gz https://lehd.ces.census.gov/data/lodes/LODES8/ky/wac/ky_wac_S000_JT00_2019.csv.gz
get data/raw/lodes/ky_xwalk.csv.gz https://lehd.ces.census.gov/data/lodes/LODES8/ky/ky_xwalk.csv.gz
get data/raw/lodes/pa_od_main_JT00_2023.csv.gz https://lehd.ces.census.gov/data/lodes/LODES8/pa/od/pa_od_main_JT00_2023.csv.gz
get data/raw/lodes/pa_wac_S000_JT00_2023.csv.gz https://lehd.ces.census.gov/data/lodes/LODES8/pa/wac/pa_wac_S000_JT00_2023.csv.gz
get data/raw/lodes/pa_xwalk.csv.gz https://lehd.ces.census.gov/data/lodes/LODES8/pa/pa_xwalk.csv.gz
get data/raw/lodes/mi_od_main_JT00_2019.csv.gz https://lehd.ces.census.gov/data/lodes/LODES8/mi/od/mi_od_main_JT00_2019.csv.gz
get data/raw/lodes/mi_wac_S000_JT00_2019.csv.gz https://lehd.ces.census.gov/data/lodes/LODES8/mi/wac/mi_wac_S000_JT00_2019.csv.gz
get data/raw/lodes/mi_xwalk.csv.gz https://lehd.ces.census.gov/data/lodes/LODES8/mi/mi_xwalk.csv.gz
get data/raw/baf/BlockAssign_ST21_KY.zip https://www2.census.gov/geo/docs/maps-data/data/baf2020/BlockAssign_ST21_KY.zip
get data/raw/baf/BlockAssign_ST42_PA.zip https://www2.census.gov/geo/docs/maps-data/data/baf2020/BlockAssign_ST42_PA.zip
get data/raw/baf/2020_Gaz_unsd_national.zip https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2020_Gazetteer/2020_Gaz_unsd_national.zip
unzip -n -q data/raw/baf/BlockAssign_ST21_KY.zip BlockAssign_ST21_KY_SDUNI.txt -d data/raw/baf
unzip -n -q data/raw/baf/BlockAssign_ST42_PA.zip BlockAssign_ST42_PA_SDUNI.txt -d data/raw/baf
unzip -n -q data/raw/baf/2020_Gaz_unsd_national.zip 2020_Gaz_unsd_national.txt -d data/raw/baf
