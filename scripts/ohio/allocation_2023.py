from pathlib import Path
import contextlib
import io
import itertools

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'output' / 'ohio'
OUT.mkdir(parents=True, exist_ok=True)
source = ROOT / 'scripts' / 'ohio' / 'allocation.py'
prefix, marker, _ = source.read_text().partition('\nres=[]')
assert marker, 'Existing model reporting boundary changed; inspect before running.'
model = {'__name__': 'allocation_baseline'}
with contextlib.redirect_stdout(io.StringIO()):
    exec(compile(prefix, str(source), 'exec'), model)
od19 = model['od'].copy()
assert not od19[['hp', 'wp']].isna().any().any()

crosswalk = pd.read_csv(ROOT / 'data/raw/lodes/oh_xwalk.csv.gz',
                        usecols=['tabblk2020', 'stplc'], dtype=str)
assert crosswalk.tabblk2020.is_unique
mapping = crosswalk.set_index('tabblk2020').stplc
cols = ['S000', 'SE01', 'SE02', 'SE03']
parts, jobs, unmapped = [], 0, 0
for chunk in pd.read_csv(ROOT / 'data/raw/lodes/oh_od_main_JT00_2023.csv.gz',
                         usecols=['w_geocode', 'h_geocode'] + cols,
                         dtype={'w_geocode': str, 'h_geocode': str},
                         chunksize=500_000):
    assert chunk.w_geocode.str.startswith('39').all()
    assert chunk.h_geocode.str.startswith('39').all()
    assert (chunk.SE01 + chunk.SE02 + chunk.SE03 == chunk.S000).all()
    chunk['wp'] = chunk.w_geocode.map(mapping)
    chunk['hp'] = chunk.h_geocode.map(mapping)
    bad = chunk[['wp', 'hp']].isna().any(axis=1)
    unmapped += int(chunk.loc[bad, 'S000'].sum())
    assert not bad.any(), 'Missing block mapping must not become an untaxed place.'
    parts.append(chunk.groupby(['hp', 'wp'])[cols].sum())
    jobs += int(chunk.S000.sum())
od23 = pd.concat(parts).groupby(level=['hp', 'wp']).sum().reset_index()
assert int(od23.S000.sum()) == jobs
od23.to_csv(OUT / 'od_place_2023_bands.csv.gz', index=False)

all_places = set(od19.hp) | set(od19.wp) | set(od23.hp) | set(od23.wp)
classification = {p: model['classify'](p) for p in all_places}
for p in all_places:
    if p in model['amb_codes'] and p not in model['Sc'].index:
        classification[p] = 'unresolved (ambiguous name)'
for p in model['NO_TAX_20191231']:
    if p in classification:
        classification[p] = 'no tax per ODT list'
model['C'] = classification
weights = {
    'base 800/2300/6000': {'SE01': 800, 'SE02': 2300, 'SE03': 6000},
    'low 600/2000/4500': {'SE01': 600, 'SE02': 2000, 'SE03': 4500},
    'high 1000/2800/9000': {'SE01': 1000, 'SE02': 2800, 'SE03': 9000},
}
rows, by_residence, diagnostics, exclusions = [], [], [], []
for year, od in [(2019, od19), (2023, od23)]:
    model['od'] = od
    for (label, w), tele, unknown in itertools.product(weights.items(), ['DN', 'uniform'], ['low', 'high']):
        share, unknown_share, d = model['run'](w, tele, unknown)
        missing = d.t_w.isna() | d.cr.isna()
        if label.startswith('base') and tele == 'DN' and unknown == 'low':
            for code, z in d.loc[missing].groupby('wp'):
                name = model['pl'].set_index('stplc').PLACENAME.get(code, code)
                exclusions.append(dict(flow_year=year, workplace=code,
                    name=name, jobs=int(z.S000.sum()), reason='Missing workplace tax rate in existing baseline model'))
        d = d.loc[~missing].copy()
        assert np.isfinite(d[['earn', 'tw', 't_w', 't_r', 'cr']].to_numpy()).all()
        loss = d.earn * d.tw * d.t_w / 100
        gain = d.earn * d.tw * d.cr / 100
        total_loss, total_gain = float(loss.sum()), float(gain.sum())
        assert total_loss > 0 and 0 <= share <= 1
        rows.append(dict(flow_year=year, earnings=label, teleworkability=tele,
                         unknowns=unknown, residence_share=float(share),
                         worker_share=1-float(share), unknown_loss_share=float(unknown_share),
                         workplace_loss_dollars=total_loss, residence_gain_dollars=total_gain,
                         worker_savings_dollars=total_loss-total_gain,
                         modeled_commuter_jobs=int(d.S000.sum())))
        if label.startswith('base') and tele == 'DN' and unknown == 'low':
            tab = pd.DataFrame({'residence_class': d.rcls, 'loss': loss, 'gain': gain})
            for cls, z in tab.groupby('residence_class'):
                by_residence.append(dict(flow_year=year, residence_class=cls,
                    workplace_loss_share=float(z.loss.sum()/total_loss),
                    worker_savings_per_total_loss=float((z.loss.sum()-z.gain.sum())/total_loss)))
            diagnostics.append(dict(flow_year=year, all_instate_jobs=int(od.S000.sum()),
                                    place_pairs=len(od), modeled_commuter_jobs=int(d.S000.sum())))

result = pd.DataFrame(rows)
baseline = pd.read_csv(ROOT / 'output/ohio/allocation_sensitivity.csv')
actual = result[result.flow_year == 2019].set_index(['earnings', 'teleworkability', 'unknowns'])
for r in baseline.itertuples(index=False, name=None):
    a = actual.loc[(r[0], r[1], r[2])]
    assert abs(a.residence_share - r[3]) <= 0.000501
    assert abs(a.worker_share - r[4]) <= 0.000501
result.to_csv(OUT / 'allocation_2023_comparison.csv', index=False)
pd.DataFrame(by_residence).to_csv(OUT / 'allocation_2023_by_residence.csv', index=False)
pd.DataFrame(exclusions).to_csv(OUT / 'allocation_2023_scope_exclusions.csv', index=False)

main = result[(result.earnings == 'base 800/2300/6000') &
              (result.teleworkability == 'DN') & (result.unknowns == 'low')].set_index('flow_year')
for year in [2019, 2023]:
    z = result[result.flow_year == year]
    print(year, round(100*main.loc[year, 'worker_share'], 2), round(100*z.worker_share.min(), 2), round(100*z.worker_share.max(), 2))
