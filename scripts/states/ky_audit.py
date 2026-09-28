import runpy, sys, json
import pandas as pd

sc = sys.argv[1:] or ['--overlap', 'stacked', '--unres', 'mid', '--bands', 'base']
sys.argv = ['ky_statewide.py'] + sc
g = runpy.run_path('scripts/states/ky_statewide.py')
agg, GRID, BANDS, CITY, COUNTY = g['agg'], g['GRID'], g['BANDS'], g['CITY'], g['COUNTY']

cr = pd.read_csv('data/kentucky/county_rates_2019_final.csv')
ct = pd.read_csv('data/kentucky/city_rates_2019_final.csv')
ccls = dict(zip(cr.county + ' County', cr.rate_2019_evidence + '/' + cr.tax_existed_2019))
tcls = dict(zip(ct.city, ct.rate_2019_evidence + '/' + ct.tax_existed_2019))

def cls(k):
    if k in ('Louisville Metro', 'Lexington-Fayette', 'Boone County Schools'):
        return 'verified_2019/yes'
    if k in ccls:
        return ccls[k]
    if k in tcls:
        return tcls[k]
    return 'unresolved'

flow_unres = {'wp': [0, 0, 0], 'hp': [0, 0, 0]}
vset = {k for k, v in tcls.items() if v.startswith('verified_2019')}
bycls = {}
for r in agg.itertuples(index=False):
    for b in BANDS:
        n = getattr(r, b) * r.tele
        e, wt = GRID[b]
        earn = getattr(r, b) * (e * wt).sum()
        if n == 0:
            continue
        bt, u1 = g['layers'](r.wc, r.wp, r.wsd, e, r.hc, r.hsd)
        for k, v in bt.items():
            c = cls(k)
            bycls[c] = bycls.get(c, 0) + n * (v * wt).sum()
        for side, cc, pp in (('wp', r.wc, r.wp), ('hp', r.hc, r.hp)):
            if pp:
                flow_unres[side][0] += earn
                if cc == 'Fayette' or (cc == 'Jefferson' and pp == 'Louisville'):
                    flow_unres[side][1] += earn
                    flow_unres[side][2] += earn
                elif (cc, pp) in CITY:
                    flow_unres[side][1] += earn
                    if pp in vset:
                        flow_unres[side][2] += earn
tot = sum(bycls.values())
out = {'scenario': ' '.join(sc), 'tax_before_m': tot / 1e6,
       'share_by_class': {k: round(v / tot, 4) for k, v in sorted(bycls.items())},
       'city_work_earn_documented': flow_unres['wp'][1] / flow_unres['wp'][0],
       'city_home_earn_documented': flow_unres['hp'][1] / flow_unres['hp'][0],
       'city_work_earn_verified2019': flow_unres['wp'][2] / flow_unres['wp'][0],
       'city_home_earn_verified2019': flow_unres['hp'][2] / flow_unres['hp'][0],
       'unres_share_touching': g['res']['unres_share']}
print('AUDIT ' + json.dumps(out))
