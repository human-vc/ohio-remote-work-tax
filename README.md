# The Revenue That Doesn't Return: Remote Work and Local Income Taxes

Replication code and data for Jacob Crainic, "The Revenue That Doesn't Return: Remote Work and Local Income Taxes."

## Run

```
./run_all.sh
```

Requires Python 3.14, `curl` and `unzip`. The script creates `.venv`, installs `requirements.txt`, downloads the public LODES, Census, IRS SOI, Ohio Department of Taxation and NCES files into `data/raw/`, and runs every step. Results go to `output/`, logs to `output/logs/`. The Rambachan–Roth sensitivity step also needs R 4.5 with `HonestDiD` 0.2.8 and is skipped if `Rscript` is not found.

## Steps

1. `scripts/ohio/run.sh`: 2019 Ohio tax schedule, exposure and allocation simulation
2. `scripts/revenue/run.sh`: revenue samples, event-study and component estimates
3. `scripts/states/run.sh`: Michigan, Pennsylvania and Kentucky calculations

## Data

- `data/ohio/baseline_schedule_2019_12_31.csv`, `data/ohio/nonrita_schedule_2019.csv`: the constructed 2019 municipal tax schedule
- `data/ohio/rita_mdr_cash_ytd.csv`: cash collections by component from the Regional Income Tax Agency's November distribution reports, 2019–2024, obtained by public records request; `scripts/revenue/mdr_parse.py <pdf folder>` rebuilds it from the PDFs
- `data/ohio/refunds_for_remote_work.csv`: city-reported refunds for work done at home, with sources
- `data/ohio/acs1_b08301_oh_wfh.csv`: Ohio workers who usually worked from home, ACS 2015–2023
- `data/kentucky/`, `data/michigan/`, `data/pennsylvania/`: comparison-state rates and rules
