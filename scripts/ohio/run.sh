#!/bin/sh
set -e
PY=${PY:-.venv/bin/python}
mkdir -p output/ohio output/logs
for s in teleworkability exposure controls allocation counterfactuals allocation_flow_industry allocation_details allocation_2023 residence_pattern gleeson_comparison acs_township; do
  $PY scripts/ohio/$s.py > output/logs/ohio_$s.log 2>&1
done
