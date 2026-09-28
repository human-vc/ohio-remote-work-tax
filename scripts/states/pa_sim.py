import argparse
import json

import numpy as np
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument('--philly', default='voluntary', choices=['voluntary', 'required'])
ap.add_argument('--bands', default='base', choices=['low', 'base', 'high'])
ap.add_argument('--taxing-work', action='store_true')
ap.add_argument('--muni-only', action='store_true')
args = ap.parse_args()

BANDS = {'low': (600, 2000, 4500), 'base': (800, 2300, 6000), 'high': (1000, 2800, 9000)}[args.bands]
BANDS = dict(zip(['SE01', 'SE02', 'SE03'], [12 * m for m in BANDS]))
PHL_NR = 3.44

reg = pd.read_csv('output/states/psd_rates_2023_07.csv', dtype={'psd': str}).drop_duplicates('psd').set_index('psd')
bm = pd.read_csv('output/states/block_psd_map.csv.gz', dtype=str).set_index('tabblk2020')
k = bm.k

od = pd.read_csv('data/raw/lodes/pa_od_main_JT00_2023.csv.gz', dtype={'w_geocode': str, 'h_geocode': str},
                 usecols=['w_geocode', 'h_geocode', 'SE01', 'SE02', 'SE03'])
od['hk'], od['wk'] = od.h_geocode.map(k), od.w_geocode.map(k)
od['hpsd'], od['wpsd'] = od.h_geocode.map(bm.psd), od.w_geocode.map(bm.psd)
od = od[(od.hk != od.wk) & (od.hpsd.isna() | (od.hpsd != od.wpsd))]

dn = pd.read_csv('data/ohio/NAICS_workfromhome.csv', dtype={'NAICS': str})
sc = dict(zip(dn.NAICS, dn.teleworkable_emp))
cns = {'CNS01': '11', 'CNS02': '21', 'CNS03': '22', 'CNS04': '23', 'CNS05': '31-33', 'CNS06': '42', 'CNS07': '44-45',
       'CNS08': '48-49', 'CNS09': '51', 'CNS10': '52', 'CNS11': '53', 'CNS12': '54', 'CNS13': '55', 'CNS14': '56',
       'CNS15': '61', 'CNS16': '62', 'CNS17': '71', 'CNS18': '72', 'CNS19': '81', 'CNS20': '92'}
use = [c for c, v in cns.items() if v in sc]
wac = pd.read_csv('data/raw/lodes/pa_wac_S000_JT00_2023.csv.gz', dtype={'w_geocode': str})
wac['wk'] = wac.w_geocode.map(k)
g = wac.groupby('wk')[use].sum()
tele = (sum(g[c] * sc[cns[c]] for c in use) / g[use].sum(axis=1)).rename('tele')

agg = od.groupby(['hpsd', 'wpsd', 'hk', 'wk'], dropna=False)[list(BANDS)].sum().reset_index().join(tele, on='wk')
agg['E'] = sum(agg[b] * v for b, v in BANDS.items()) * agg.tele.fillna(agg.tele.mean())
tot_E = agg.E.sum()
ok = agg.hpsd.notna() & agg.wpsd.notna()
cov = agg[ok].E.sum() / tot_E
a = agg[ok].copy()

T_h = a.hpsd.map(reg.tot).values
N_w = a.wpsd.map(reg.nr).values
h_phl = (a.hpsd.map(reg.muni) == 'PHILADELPHIA CITY').values
w_phl = (a.wpsd.map(reg.muni) == 'PHILADELPHIA CITY').values
E = a.E.values

H = a.hpsd.map(reg.mr).values if args.muni_only else T_h
home_b = np.where(w_phl & ~h_phl, np.maximum(H - PHL_NR, 0), H)
work_b = np.where(w_phl & ~h_phl, PHL_NR, np.where(h_phl, 0.0, np.maximum(N_w - T_h, 0)))
home_a = H.copy()
work_a = np.zeros_like(T_h)
keep = w_phl & ~h_phl & (args.philly == 'voluntary')
home_a[keep], work_a[keep] = home_b[keep], work_b[keep]

B = E * (home_b + work_b) / 100
A = E * (home_a + work_a) / 100
loss = E * (np.maximum(home_b - home_a, 0) + np.maximum(work_b - work_a, 0)) / 100
gain = E * (np.maximum(home_a - home_b, 0) + np.maximum(work_a - work_b, 0)) / 100
kept = E * (np.minimum(home_b, home_a) + np.minimum(work_b, work_a)) / 100

sel = (N_w > 0) | w_phl if args.taxing_work else np.ones(len(a), bool)


def summ(mask):
    mask = mask & sel
    L, G, Bt = loss[mask].sum(), gain[mask].sum(), B[mask].sum()
    return {'tax_before_m': round(Bt / 1e6, 2), 'exposed_share': round(L / Bt, 4) if Bt else None,
            'kept_share': round(kept[mask].sum() / Bt, 4) if Bt else None,
            'loss_m': round(L / 1e6, 2), 'loss_to_govts': round(G / L, 4) if L else None,
            'loss_to_workers': round((L - G) / L, 4) if L else None,
            'net_reduction_share': round((L - G) / Bt, 4) if Bt else None,
            'tele_earn_bn': round(E[mask].sum() / 1e9, 3)}


out = {'philly': args.philly, 'bands': args.bands, 'taxing_work': args.taxing_work, 'muni_only': args.muni_only, 'coverage_earnings': round(cov, 4),
       'coverage_rows': round(ok.mean(), 4),
       'statewide': summ(np.ones(len(a), bool)),
       'act32_outside_philadelphia': summ(~w_phl & ~h_phl),
       'philadelphia_workplace': summ(w_phl & ~h_phl),
       'philadelphia_residents_elsewhere': summ(h_phl & ~w_phl)}
print(json.dumps(out))
