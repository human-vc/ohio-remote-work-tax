#!/bin/sh
set -e
mkdir -p output/states
for o in stacked credited; do for u in low mid high; do for b in low base high; do for a in zero rate; do .venv/bin/python scripts/states/ky_statewide.py --overlap $o --unres $u --bands $b --adopters $a --keep-verified-no; done; done; done; done > output/states/ky_grid.jsonl
for u in low mid high; do for b in low base high; do for a in zero rate; do .venv/bin/python scripts/states/ky_statewide.py --overlap credited --unres $u --bands $b --adopters $a; done; done; done > output/states/ky_statutory_credit.jsonl
for o in stacked credited; do for u in low mid high; do .venv/bin/python scripts/states/ky_statewide.py --nky --no-school --keep-verified-no --overlap $o --unres $u --bands base; done; done > output/states/ky_panel_c.jsonl
.venv/bin/python scripts/states/ky_audit.py --overlap stacked --unres mid --bands base --adopters zero --keep-verified-no | grep '^AUDIT ' | sed 's/^AUDIT //' > output/states/ky_audit.json
.venv/bin/python scripts/states/sens_open_items.py
for o in stacked credited; do for u in low mid high; do .venv/bin/python scripts/states/nky_pilot.py --overlap $o --unres $u --bands base --schools none; done; done > output/states/nky_pilot.jsonl
.venv/bin/python scripts/states/build_psd_map.py
{
.venv/bin/python scripts/states/pa_sim.py --philly voluntary
.venv/bin/python scripts/states/pa_sim.py --philly voluntary --taxing-work
.venv/bin/python scripts/states/pa_sim.py --philly voluntary --muni-only
.venv/bin/python scripts/states/pa_sim.py --philly voluntary --taxing-work --muni-only
.venv/bin/python scripts/states/pa_sim.py --philly required
} > output/states/pa_grid.jsonl
.venv/bin/python scripts/states/build_mi.py
.venv/bin/python scripts/states/compare_oh_mi.py
.venv/bin/python scripts/states/summarize.py
