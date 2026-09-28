# The Revenue That Doesn't Return: Remote Work and Local Income Taxes

Replication code and data for Jacob Crainic, "The Revenue That Doesn't Return: Remote Work and Local Income Taxes."

## Requirements

- Python 3.14 (tested with 3.14.7)
- R 4.5 with the `HonestDiD` package (0.2.8), used only by `scripts/revenue/honestdid.R`
- `curl` and `unzip` for the public downloads

```
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## Run

```
./run_all.sh
```

This runs, in order:

1. `scripts/ohio/download.sh`, `scripts/states/download.sh`: public LODES, Census block assignment, IRS SOI, Ohio Department of Taxation and NCES files into `data/raw/`
2. `scripts/ohio/run.sh`: Ohio tax schedule, exposure and allocation simulation
3. `scripts/revenue/run.sh`: revenue samples and event-study estimates (bootstrap B = 1999, 999 where noted in the script)
4. `scripts/states/run.sh`: Michigan, Pennsylvania and Kentucky calculations

Results are written to `output/` as CSV and JSON, with console logs in `output/logs/`.
