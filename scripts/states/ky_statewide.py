import argparse, json
import numpy as np
import pandas as pd

ap = argparse.ArgumentParser()
ap.add_argument('--overlap', default='stacked', choices=['stacked', 'credited'])
ap.add_argument('--unres', default='mid', choices=['low', 'mid', 'high'])
ap.add_argument('--bands', default='base', choices=['low', 'base', 'high'])
ap.add_argument('--point', action='store_true')
ap.add_argument('--ntail', type=int, default=300)
ap.add_argument('--by-gov', action='store_true')
ap.add_argument('--adopters', default='zero', choices=['zero', 'rate'])
ap.add_argument('--nky', action='store_true')
ap.add_argument('--drop-big', action='store_true')
ap.add_argument('--no-school', action='store_true')
ap.add_argument('--keep-verified-no', action='store_true')
args = ap.parse_args()

FICA = 132900.0
BANDS = {'low': (600, 2000, 4500), 'base': (800, 2300, 6000), 'high': (1000, 2800, 9000)}[args.bands]
BANDS = dict(zip(['SE01', 'SE02', 'SE03'], [12 * m for m in BANDS]))
Q = (np.arange(100) + 0.5) / 100
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
HI_CITY, MID_CITY, HI_COUNTY = 0.025, 0.0125, 0.0225
BOONE_SD = '00510'


def capped(r, cap):
    return lambda e: r * np.minimum(e, cap) if cap else r * e


def num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if np.isnan(v) else v


cr = pd.read_csv('data/kentucky/county_rates_2019_final.csv')
COUNTY, COUNTY_UNRES, COUNTY_CREDITS, COUNTY_NOCREDIT = {}, set(), set(), set()
for r in cr.itertuples():
    rate = num(r.rate_alt_pct if args.adopters == 'rate' else r.rate_2019_pct)
    if rate is None:
        COUNTY_UNRES.add(r.county)
        continue
    COUNTY[r.county] = capped(rate / 100, num(r.wage_cap)) if rate > 0 else None
    if str(r.credits_city_tax).lower() == 'yes':
        COUNTY_CREDITS.add(r.county)
    if str(r.credits_city_tax).lower() == 'no':
        COUNTY_NOCREDIT.add(r.county)
COUNTY['Boone'] = lambda e: 0.008 * np.minimum(e, 62012) + 0.0015 * np.minimum(e, 16666)
COUNTY['Kenton'] = lambda e: 0.007097 * np.minimum(e, 25000) + 0.001097 * np.clip(np.minimum(e, FICA) - 25000, 0, None)
COUNTY['Campbell'] = capped(0.0105, 38667)
COUNTY_IN_CITY = {('Pulaski', 'Somerset'): capped(0.008, None)}

ct = pd.read_csv('data/kentucky/city_rates_2019_final.csv')
pc = pd.read_csv('data/kentucky/place_county.csv').groupby('p').c.apply(list).to_dict()
CITY = {}
for r in ct.itertuples():
    rate = num(r.rate_2019_pct)
    if rate is None:
        continue
    cs = [r.only_county] if isinstance(r.only_county, str) and r.only_county else pc.get(r.city, [r.county])
    for c in cs:
        CITY[(c, r.city)] = capped(rate / 100, num(r.wage_cap)) if rate > 0 else None


def layers(c, p, sd, e, home_c, home_sd):
    out, unres = {}, np.zeros_like(e, dtype=bool)
    if c == 'Jefferson':
        out['Louisville Metro'] = (0.022 if home_c == 'Jefferson' else 0.0145) * e
    elif c == 'Fayette':
        out['Lexington-Fayette'] = 0.0225 * e
    else:
        if c in COUNTY:
            f = COUNTY_IN_CITY.get((c, p), COUNTY[c])
            if f is not None:
                out[c + ' County'] = f(e)
        else:
            unres = unres | True
            rr = {'low': 0.0, 'mid': 0.01, 'high': HI_COUNTY}[args.unres]
            if rr:
                out[c + ' County'] = rr * e
        if sd == BOONE_SD and home_sd == BOONE_SD and not args.no_school:
            out['Boone County Schools'] = 0.005 * e
    if p and not (c == 'Fayette') and not (c == 'Jefferson' and p == 'Louisville'):
        key = (c, p)
        if key in CITY:
            f = CITY[key]
            cv = f(e) if f is not None else None
        else:
            unres = unres | True
            rr = {'low': 0.0, 'mid': MID_CITY, 'high': HI_CITY}[args.unres]
            cv = rr * e if rr else None
        if cv is not None:
            out[p] = cv
            cn = c + ' County'
            credit = c in COUNTY_CREDITS or (args.overlap == 'credited' and not (args.keep_verified_no and c in COUNTY_NOCREDIT))
            if cn in out and credit:
                out[cn] = np.maximum(out[cn] - cv, 0.0)
    return out, bool(np.any(unres))


xw = pd.read_csv('data/raw/lodes/ky_xwalk.csv.gz', dtype=str, usecols=['tabblk2020', 'ctyname', 'stplcname']).set_index('tabblk2020')
sdmap = pd.read_csv('data/raw/baf/BlockAssign_ST21_KY_SDUNI.txt', sep='|', dtype=str).set_index('BLOCKID').DISTRICT


def cty(g):
    return g.map(xw.ctyname).str.replace(' County, KY', '', regex=False)


def plc(g):
    p = g.map(xw.stplcname).fillna('')
    p = p.where(~p.str.contains('CDP'), '')
    return p.str.replace(r' (city|urban county|metro government).*', '', regex=True).str.replace(r'/.*', '', regex=True)


od = pd.read_csv('data/raw/lodes/ky_od_main_JT00_2019.csv.gz', dtype={'w_geocode': str, 'h_geocode': str},
                 usecols=['w_geocode', 'h_geocode', 'SE01', 'SE02', 'SE03'])
od['wc'], od['wp'] = cty(od.w_geocode), plc(od.w_geocode)
od['hc'], od['hp'] = cty(od.h_geocode), plc(od.h_geocode)
od = od[(od.wc != od.hc) | (od.wp != od.hp)].copy()
if args.drop_big:
    od = od[~od.wc.isin(['Jefferson', 'Fayette'])].copy()
if args.nky:
    od = od[od.wc.isin(['Boone', 'Kenton', 'Campbell'])].copy()
od['wsd'] = np.where(od.w_geocode.map(sdmap) == BOONE_SD, BOONE_SD, '')
od['hsd'] = np.where(od.h_geocode.map(sdmap) == BOONE_SD, BOONE_SD, '')

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
agg = (od.groupby(['wc', 'wp', 'wsd', 'hc', 'hp', 'hsd'])[list(BANDS)].sum()
       .reset_index().join(tele, on=['wc', 'wp']))
agg['tele'] = agg.tele.fillna(agg.tele.mean())

flow = dict(before=0.0, kept=0.0, loss=0.0, gain=0.0, unres=0.0, earn=0.0, jobs=0.0)
gov = {}
for r in agg.itertuples(index=False):
    for b in BANDS:
        n = getattr(r, b) * r.tele
        if n == 0:
            continue
        e, wt = GRID[b]
        bt, u1 = layers(r.wc, r.wp, r.wsd, e, r.hc, r.hsd)
        at, u2 = layers(r.hc, r.hp, r.hsd, e, r.hc, r.hsd)
        flow['earn'] += n * (e * wt).sum()
        flow['jobs'] += n
        for k in set(bt) | set(at):
            bb = (bt[k] * wt).sum() if k in bt else 0.0
            aa = (at[k] * wt).sum() if k in at else 0.0
            kk = (np.minimum(bt.get(k, 0 * e), at.get(k, 0 * e)) * wt).sum()
            flow['before'] += n * bb
            flow['kept'] += n * kk
            flow['loss'] += n * (bb - kk)
            flow['gain'] += n * (aa - kk)
            if u1 or u2:
                flow['unres'] += n * bb
            gb, ga = gov.get(k, (0.0, 0.0))
            gov[k] = (gb + n * bb, ga + n * aa)

G = pd.DataFrame(gov, index=['before', 'after']).T
res = {
    'overlap': args.overlap, 'unres': args.unres, 'bands': args.bands, 'wages': 'point' if args.point else 'distribution',
    'tele_jobs': flow['jobs'], 'tele_earn_bn': flow['earn'] / 1e9, 'tax_before_m': flow['before'] / 1e6,
    'tax_after_m': G.after.sum() / 1e6,
    'revenue_left_per_100': 100 * G.after.sum() / G.before.sum(),
    'exposed_share': flow['loss'] / flow['before'],
    'flow_loss_to_govts': flow['gain'] / flow['loss'],
    'flow_loss_to_workers': (flow['loss'] - flow['gain']) / flow['loss'],
    'unres_share': flow['unres'] / flow['before'],
}
print(json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in res.items()}), flush=True)
if args.by_gov:
    print((G / 1e6).round(3).sort_values('before', ascending=False).head(40).to_string())
