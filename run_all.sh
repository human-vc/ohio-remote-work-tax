#!/bin/sh
set -e
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
export PY="$PWD/.venv/bin/python"
sh scripts/ohio/download.sh
sh scripts/states/download.sh
sh scripts/ohio/run.sh
sh scripts/revenue/run.sh
sh scripts/states/run.sh
echo "done: results in output/, logs in output/logs/"
