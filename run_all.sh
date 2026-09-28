#!/bin/sh
set -e
cd "$(dirname "$0")"
sh scripts/ohio/download.sh
sh scripts/states/download.sh
sh scripts/ohio/run.sh
sh scripts/revenue/run.sh
sh scripts/states/run.sh
