import argparse, json
import numpy as np
from functools import lru_cache
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument('--overlap', default='stacked', choices=['stacked', 'credited'])
ap.add_argument('--unres', default='mid', choices=['low', 'mid', 'high'])
ap.add_argument('--bands', default='base', choices=['low', 'base', 'high'])
ap.add_argument('--all-jobs', action='store_true')
ap.add_argument('--by-gov', action='store_true')
ap.add_argument('--point', action='store_true')
ap.add_argument('--ntail', type=int, default=1000)
ap.add_argument('--schools', default='none', choices=['none', 'dual', 'worksite'])
args = ap.parse_args()

FICA = 132900.0
BANDS = {'low': (600, 2000, 4500), 'base': (800, 2300, 6000), 'high': (1000, 2800, 9000)}[args.bands]
BANDS = dict(zip(['SE01', 'SE02', 'SE03'], [12 * m for m in BANDS]))
Q = (np.arange(200) + 0.5) / 200
if args.point:
    GRID = {b: (np.array([e]), np.array([1.0])) for b, e in BANDS.items()}
else:
    top = BANDS['SE03']
    alpha = top / (top - 40000.0)
    edges = np.concatenate([[0.0], np.logspace(-12, 0, args.ntail)])
    u = np.sqrt(edges[1:] * np.maximum(edges[:-1], 1e-13))
    GRID = {'SE01': (15000.0 * Q, np.full(Q.size, 1 / Q.size)),
            'SE02': (15000.0 + 25000.0 * Q, np.full(Q.size, 1 / Q.size)),
            'SE03': (40000.0 * u ** (-1 / alpha), np.diff(edges))}
BOONE_SD, WALTON_VERONA_SD = '00510', '05700'
KACO = json.load(open('data/kentucky/kaco_2024_county_rates.json'))
HI_CITY, MID_CITY, HI_OUTSIDE = 0.025, 0.0125, 0.0225
OUT_COUNTY = {'Franklin': 0.01, 'Madison': 0.01, 'Mason': 0.0, 'Clark': 0.015, 'Bourbon': 0.0075}
OUT_CITY = {'Elizabethtown': 0.0135, 'La Grange': 0.01, 'Maysville': 0.0199}
UNRES_SD = {'01530', '01740', '02040', '03090', '03630', '04440', '04740', '05700'}
SCHOOL_RATE = 0.005


def flat(r, cap=None):
    return lambda e: r * min(e, cap if cap else np.inf)


def kenton_county(e):
    return 0.007097 * min(e, 25000) + 0.001097 * max(min(e, FICA) - 25000, 0)


COUNTY = {
    'Boone': ('Boone County', lambda e: 0.008 * min(e, 62012) + 0.0015 * min(e, 16666)),
    'Kenton': ('Kenton County', kenton_county),
    'Campbell': ('Campbell County', flat(0.0105, 38667)),
    'Grant': ('Grant County', flat(0.015)),
    'Pendleton': ('Pendleton County', flat(0.005)),
    'Gallatin': ('Gallatin County', flat(0.010)),
}
CITY = {
    'Florence': flat(0.02, FICA), 'Union': None, 'Walton': None,
    'Bromley': flat(0.01), 'Covington': flat(0.0245, FICA), 'Crescent Springs': flat(0.01),
    'Crestview Hills': flat(0.0115, FICA), 'Edgewood': flat(0.01), 'Elsmere': flat(0.0125),
    'Erlanger': flat(0.015), 'Fort Mitchell': flat(0.0125), 'Fort Wright': flat(0.0115, FICA),
    'Independence': flat(0.0125), 'Lakeside Park': flat(0.01), 'Ludlow': flat(0.015),
    'Park Hills': flat(0.015, 50000), 'Ryland Heights': flat(0.01), 'Taylor Mill': flat(0.02),
    'Villa Hills': flat(0.015),
    'Fort Thomas': flat(0.0125), 'Alexandria': flat(0.015, FICA), 'Cold Spring': flat(0.01, FICA),
    'Southgate': flat(0.025), 'Highland Heights': flat(0.01, 100000), 'Newport': flat(0.025, FICA),
    'Bellevue': flat(0.025), 'Dayton': flat(0.02), 'Melbourne': None, 'Woodlawn': None,
    'Dry Ridge': flat(0.0125), 'Williamstown': None, 'Falmouth': None,
}
UNRESOLVED_CITY = {'Wilder', 'Silver Grove', 'California', 'Mentor', 'Crestview', 'Fairview', 'Kenton Vale',
                   'Crittenden', 'Corinth', 'Butler', 'Warsaw', 'Sparta', 'Glencoe'}


def taxes(cty, plc, sd, e, home_cty, home_sd):
    if cty == 'Jefferson':
        return {'Louisville Metro': (0.022 if home_cty == 'Jefferson' else 0.0145) * e}, 0
    if cty == 'Fayette':
        return {'Lexington-Fayette': 0.0225 * e}, 0
    if cty not in COUNTY:
        out, unres = {}, 0
        if cty in OUT_COUNTY:
            r = OUT_COUNTY[cty]
        else:
            unres = 1
            r = {'low': 0.0, 'mid': KACO.get(cty) or 0.0, 'high': HI_OUTSIDE}[args.unres]
        if r:
            out[cty + ' County'] = r * e
        if plc:
            if plc in OUT_CITY:
                c = OUT_CITY[plc]
            else:
                unres = unres | 1
                c = {'low': 0.0, 'mid': MID_CITY, 'high': HI_CITY}[args.unres]
            if c:
                out[plc] = c * e
        return out, unres
    name, f = COUNTY[cty]
    out, unres = {name: f(e)}, 0
    if sd == BOONE_SD and home_sd == BOONE_SD:
        out['Boone County Schools'] = 0.005 * e
    if sd in UNRES_SD:
        unres = unres | 2
        if args.schools == 'worksite' or (args.schools == 'dual' and home_sd == sd):
            out['school ' + sd] = SCHOOL_RATE * e
    c = 0.0
    if plc in CITY and CITY[plc] is not None:
        c = CITY[plc](e)
    elif plc in UNRESOLVED_CITY:
        unres = unres | 1
        c = {'low': 0.0, 'mid': MID_CITY * e, 'high': HI_CITY * e}[args.unres]
    if c:
        out[plc] = c
        if args.overlap == 'credited' and cty in ('Boone', 'Kenton', 'Campbell'):
            out[name] = max(out[name] - c, 0.0)
    return out, unres


xw = pd.read_csv('data/raw/lodes/ky_xwalk.csv.gz', dtype=str, usecols=['tabblk2020', 'ctyname', 'stplcname']).set_index('tabblk2020')
sd = pd.read_csv('data/raw/baf/BlockAssign_ST21_KY_SDUNI.txt', sep='|', dtype=str).set_index('BLOCKID').DISTRICT


def cty(g):
    return g.map(xw.ctyname).str.replace(' County, KY', '', regex=False)


def plc(g):
    p = g.map(xw.stplcname).fillna('')
    p = p.where(~p.str.contains('CDP'), '')
    return p.str.replace(r' (city|urban county|metro government).*', '', regex=True).str.replace(r'/.*', '', regex=True)


od = pd.read_csv('data/raw/lodes/ky_od_main_JT00_2019.csv.gz', dtype={'w_geocode': str, 'h_geocode': str},
                 usecols=['w_geocode', 'h_geocode', 'SE01', 'SE02', 'SE03'])
od = od[od.w_geocode.str[:5].isin({'21015', '21117', '21037'})].copy()
od['wc'], od['wp'], od['wsd'] = cty(od.w_geocode), plc(od.w_geocode), od.w_geocode.map(sd)
od['hc'], od['hp'], od['hsd'] = cty(od.h_geocode), plc(od.h_geocode), od.h_geocode.map(sd)
if not args.all_jobs:
    od = od[(od.wc != od.hc) | (od.wp != od.hp)]

wac = pd.read_csv('data/raw/lodes/ky_wac_S000_JT00_2019.csv.gz', dtype={'w_geocode': str})
dn = pd.read_csv('data/ohio/NAICS_workfromhome.csv', dtype={'NAICS': str})
sc = dict(zip(dn.NAICS, dn.teleworkable_emp))
cns = {'CNS01': '11', 'CNS02': '21', 'CNS03': '22', 'CNS04': '23', 'CNS05': '31-33', 'CNS06': '42', 'CNS07': '44-45',
       'CNS08': '48-49', 'CNS09': '51', 'CNS10': '52', 'CNS11': '53', 'CNS12': '54', 'CNS13': '55', 'CNS14': '56',
       'CNS15': '61', 'CNS16': '62', 'CNS17': '71', 'CNS18': '72', 'CNS19': '81', 'CNS20': '92'}
use = [k for k, v in cns.items() if v in sc]
wac['wc'], wac['wp'] = cty(wac.w_geocode), plc(wac.w_geocode)
g = wac.groupby(['wc', 'wp'])[use].sum()
tele = (sum(g[k] * sc[cns[k]] for k in use) / g[use].sum(axis=1)).rename('tele')

agg = (od.groupby(['wc', 'wp', 'wsd', 'hc', 'hp', 'hsd'], dropna=False)[list(BANDS)].sum()
       .reset_index().join(tele, on=['wc', 'wp']))


@lru_cache(maxsize=None)
def band_pair(wloc, hloc, b, home_cty, home_sd):
    acc, un = {}, 0
    for e, wt in zip(*GRID[b]):
        bt, u1 = taxes(*wloc, e, home_cty, home_sd)
        at, u2 = taxes(*hloc, e, home_cty, home_sd)
        un = un | u1 | u2
        for k in set(bt) | set(at):
            bb, aa = bt.get(k, 0.0), at.get(k, 0.0)
            x = acc.setdefault(k, np.zeros(5))
            x += wt * np.array([bb, aa, min(bb, aa), max(bb - aa, 0.0), max(aa - bb, 0.0)])
    return acc, un


flow = dict(before=0.0, kept=0.0, loss=0.0, gain=0.0, unres_rate=0.0, unres_school=0.0, earn=0.0)
gov = {}
for r in agg.itertuples():
    for b in BANDS:
        n = getattr(r, b) * r.tele
        if n == 0:
            continue
        acc, un = band_pair((r.wc, r.wp, r.wsd), (r.hc, r.hp, r.hsd), b, r.hc, r.hsd)
        flow['earn'] += n * (GRID[b][0] * GRID[b][1]).sum()
        for k, (bb, aa, kk, ll, gg) in acc.items():
            flow['before'] += n * bb
            flow['kept'] += n * kk
            flow['loss'] += n * ll
            flow['gain'] += n * gg
            if un & 1:
                flow['unres_rate'] += n * bb
            if un & 2:
                flow['unres_school'] += n * bb
            gb, ga = gov.get(k, (0.0, 0.0))
            gov[k] = (gb + n * bb, ga + n * aa)

G = pd.DataFrame(gov, index=['before', 'after']).T
net_loss = (G.before - G.after).clip(lower=0).sum()
net_gain = (G.after - G.before).clip(lower=0).sum()
res = {
    'overlap': args.overlap, 'unres': args.unres, 'bands': args.bands, 'schools': args.schools,
    'sample': 'all jobs' if args.all_jobs else 'commuters', 'wages': 'point' if args.point else 'distribution',
    'top_band_mean': float((GRID['SE03'][0] * GRID['SE03'][1]).sum()),
    'tele_earn_bn': flow['earn'] / 1e9, 'tax_before_m': flow['before'] / 1e6,
    'flow_kept_share': flow['kept'] / flow['before'],
    'flow_loss_m': flow['loss'] / 1e6,
    'flow_loss_to_govts': flow['gain'] / flow['loss'],
    'flow_loss_to_workers': (flow['loss'] - flow['gain']) / flow['loss'],
    'gov_net_kept_share': np.minimum(G.before, G.after).sum() / G.before.sum(),
    'gov_net_loss_to_workers': (net_loss - net_gain) / net_loss,
    'unres_rate_share': flow['unres_rate'] / flow['before'],
    'unres_school_share': flow['unres_school'] / flow['before'],
}
print(json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in res.items()}))
if args.by_gov:
    print((G / 1e6).round(3).sort_values('before', ascending=False).to_string())
