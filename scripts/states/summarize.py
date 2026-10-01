import itertools
import json

import pandas as pd

O = 'output/states/'


def jl(f):
    return [json.loads(l) for l in open(O + f) if l.strip()]


def rng(X, k, m=1):
    v = [m * d[k] for d in X]
    return min(v), max(v)


rows = []


def add(exhibit, row, measure, lo, hi=None):
    rows.append((exhibit, row, measure, lo, lo if hi is None else hi))


def four(exhibit, row, X, left='revenue_left_per_100', exp='exposed_share', gov='flow_loss_to_govts', wrk='flow_loss_to_workers'):
    add(exhibit, row, 'revenue left per $100', *rng(X, left))
    add(exhibit, row, 'tax exposed %', *rng(X, exp, 100))
    add(exhibit, row, 'other govts %', *rng(X, gov, 100))
    add(exhibit, row, 'workers %', *rng(X, wrk, 100))


A = pd.read_csv(O + 'oh_mi_accounting.csv').set_index('state')
for s in ['Ohio', 'Michigan']:
    four('tab:comparison', s, [A.loc[s].to_dict()], gov='loss_to_govts', wrk='loss_to_workers')

P = {(d['philly'], d['taxing_work'], d['muni_only']): d for d in jl('pa_grid.jsonl')}
for d in P.values():
    for x in d.values():
        if isinstance(x, dict):
            x['revenue_left_per_100'] = 100 * (1 - x['net_reduction_share'])
four('tab:comparison', 'Pennsylvania', [P['voluntary', True, True]['act32_outside_philadelphia']], gov='loss_to_govts', wrk='loss_to_workers')

G = jl('ky_grid.jsonl')
four('tab:comparison', 'Kentucky', G)

for name, k in [('Philadelphia, voluntary remote', 'voluntary'), ('Philadelphia, required remote', 'required')]:
    x = P[k, False, False]['philadelphia_workplace']
    add('tab:comparison', name, 'revenue left per $100', x['revenue_left_per_100'])
    add('tab:comparison', name, 'tax exposed %', 100 * x['exposed_share'])
    if x['loss_m']:
        add('tab:comparison', name, 'other govts %', 100 * x['loss_to_govts'])
        add('tab:comparison', name, 'workers %', 100 * x['loss_to_workers'])

for name, k, part in [('Act 32, all flows and taxes', ('voluntary', False, False), 'act32_outside_philadelphia'),
                      ('Act 32, taxing workplaces', ('voluntary', True, False), 'act32_outside_philadelphia'),
                      ('Act 32, municipal only', ('voluntary', False, True), 'act32_outside_philadelphia'),
                      ('Act 32, both (Ohio scope)', ('voluntary', True, True), 'act32_outside_philadelphia'),
                      ('Philadelphia, voluntary remote', ('voluntary', False, False), 'philadelphia_workplace'),
                      ('Philadelphia, required remote', ('required', False, False), 'philadelphia_workplace'),
                      ('Philadelphia residents elsewhere', ('voluntary', False, False), 'philadelphia_residents_elsewhere'),
                      ('Statewide, voluntary', ('voluntary', False, False), 'statewide'),
                      ('Statewide, required', ('required', False, False), 'statewide')]:
    x = P[k][part]
    add('tab:a_pennsylvania', name, 'tax $m', x['tax_before_m'])
    add('tab:a_pennsylvania', name, 'exposed %', 100 * x['exposed_share'])
    add('tab:a_pennsylvania', name, 'net loss %', 100 * x['net_reduction_share'])
    if x['loss_m']:
        add('tab:a_pennsylvania', name, 'workers %', 100 * x['loss_to_workers'])
add('tab:a_pennsylvania', 'Commuting earnings matching a rate', '%', 100 * P['voluntary', False, False]['coverage_earnings'])

cr = pd.read_csv('data/kentucky/county_rates_2019_final.csv')
ct = pd.read_csv('data/kentucky/city_rates_2019_final.csv')
au = json.load(open(O + 'ky_audit.json'))
add('tab:a_kentucky_state', 'Counties levying a wage tax', 'count', int((cr.rate_2019_pct > 0).sum()))
add('tab:a_kentucky_state', 'Counties with rates verified for 2019', 'count', int((cr.rate_2019_evidence == 'verified_2019').sum()))
add('tab:a_kentucky_state', 'Cities in the schedule', 'count', len(ct))
add('tab:a_kentucky_state', 'Cities verified for 2019', 'count', int((ct.rate_2019_evidence == 'verified_2019').sum()))
add('tab:a_kentucky_state', 'Earnings worked in listed cities', '%', 100 * au['city_work_earn_documented'])
add('tab:a_kentucky_state', "Earnings of listed cities' residents", '%', 100 * au['city_home_earn_documented'])
add('tab:a_kentucky_state', 'Tax at rates verified for 2019', '%', 100 * au['share_by_class']['verified_2019/yes'])
add('tab:a_kentucky_state', 'Tax in flows with unresolved rates', '%', *rng(G, 'unres_share', 100))

for name, fn in [('Taxes stacked', lambda d: d['overlap'] == 'stacked'), ('City tax credited', lambda d: d['overlap'] == 'credited'),
                 ('Unresolved rates: zero', lambda d: d['unres'] == 'low'), ('Unresolved rates: middle', lambda d: d['unres'] == 'mid'),
                 ('Unresolved rates: high', lambda d: d['unres'] == 'high'), ('All 36', lambda d: True)]:
    four('tab:a_kentucky_state', name, [d for d in G if fn(d)])
four('tab:a_kentucky_state', 'Statewide method and inputs', jl('ky_panel_c.jsonl'))
N = jl('nky_pilot.jsonl')
add('tab:a_kentucky_state', 'Three-county calculation', 'other govts %', *rng(N, 'flow_loss_to_govts', 100))
add('tab:a_kentucky_state', 'Three-county calculation', 'workers %', *rng(N, 'flow_loss_to_workers', 100))

add('app:comparison', 'Counties with documented 2019 credit practice', 'count', int(cr.credits_city_tax.isin(['yes', 'no']).sum()))
add('app:comparison', 'Counties documented as not crediting city tax', 'count', int((cr.credits_city_tax == 'no').sum()))
add('app:comparison', 'Kentucky scenarios', 'count', len(G))
add('app:comparison', 'City tax credited, documented 2019 practice', 'revenue left per $100', *rng([d for d in G if d['overlap'] == 'credited'], 'revenue_left_per_100'))
add('app:comparison', 'City tax credited, statutory credit in all counties', 'revenue left per $100', *rng(jl('ky_statutory_credit.jsonl'), 'revenue_left_per_100'))

V = jl('sens_open_items.jsonl')
combos = list(itertools.product(['stacked', 'credited'], ['low', 'mid', 'high'], ['low', 'base', 'high'], ['zero', 'rate']))
for i, d in enumerate(V):
    o, u, b, a = combos[i % 36]
    assert (d['overlap'], d['unres'], d['bands']) == (o, u, b)
    d['adopters'] = a


def key(d):
    return d['overlap'], d['unres'], d['bands'], d['adopters']


base ={key(d): d for d in V if d['variant'] == 'base'}
add('app:comparison', 'Open items', 'largest change in revenue left per $100', max(abs(d['revenue_left_per_100'] - base[key(d)]['revenue_left_per_100']) for d in V))
add('app:comparison', 'Open items', 'largest change in worker share, points', max(abs(100 * (d['flow_loss_to_workers'] - base[key(d)]['flow_loss_to_workers'])) for d in V))

mi = pd.read_csv('data/michigan/mi_rate_status_2019.csv')
add('app:comparison', 'Michigan cities levying the tax', 'count', len(mi))
add('app:comparison', 'Michigan rates from 2019 documents', 'count', int(mi.evidence_class.str.startswith('direct_2019').sum()))

out = pd.DataFrame(rows, columns=['exhibit', 'row', 'measure', 'low', 'high'])
out[['low', 'high']] = out[['low', 'high']].astype(float).round(4)
out.to_csv(O + 'paper_numbers.csv', index=False)
print(out.to_string(index=False))
