import pandas as pd, numpy as np, os, itertools, json
exec(open('scripts/ohio/allocation.py').read().split("res=[]")[0])

CNS = {'CNS01':'11','CNS02':'21','CNS03':'22','CNS04':'23','CNS05':'31-33','CNS06':'42','CNS07':'44-45','CNS08':'48-49','CNS09':'51','CNS10':'52','CNS11':'53','CNS12':'54','CNS13':'55','CNS14':'56','CNS15':'61','CNS16':'62','CNS17':'71','CNS18':'72','CNS19':'81','CNS20':'92'}
SUPER = {'SI01':['CNS01','CNS02','CNS04','CNS05'],'SI02':['CNS03','CNS06','CNS07','CNS08'],'SI03':[f'CNS{i:02d}' for i in range(9,21)]}
dn = pd.read_csv('data/ohio/NAICS_workfromhome.csv', dtype={'NAICS':str})
sc = dict(zip(dn.NAICS, dn.teleworkable_emp))
used = [k for k, v in CNS.items() if v in sc]
print('sectors with a Dingel-Neiman value:', len(used), '| dropped:', [k for k in CNS if k not in used])

xw = pd.read_csv('data/raw/lodes/oh_xwalk.csv.gz', usecols=['tabblk2020','stplc'], dtype=str)
blk = dict(zip(xw.tabblk2020, xw.stplc))

odsi_path = 'output/ohio/od_place_2019_si.csv.gz'
if not os.path.exists(odsi_path):
    cols = ['S000','SE01','SE02','SE03','SI01','SI02','SI03']
    parts = []
    for ch in pd.read_csv('data/raw/lodes/oh_od_main_JT00_2019.csv.gz', usecols=['w_geocode','h_geocode']+cols, dtype={'w_geocode':str,'h_geocode':str}, chunksize=1_000_000):
        ch['wp'] = ch.w_geocode.map(blk).fillna('9999999'); ch['hp'] = ch.h_geocode.map(blk).fillna('9999999')
        parts.append(ch.groupby(['hp','wp'])[cols].sum())
    pd.concat(parts).groupby(level=[0,1]).sum().reset_index().to_csv(odsi_path, index=False)
odsi = pd.read_csv(odsi_path, dtype={'hp':str,'wp':str})

chk = od.merge(odsi, on=['hp','wp'], how='outer', suffixes=('_b',''), indicator=True)
print('flow match with bands file:', chk._merge.value_counts().to_dict(),
      '| max abs diff S000/SE:', max((chk[f'{c}_b']-chk[c]).abs().max() for c in ['S000','SE01','SE02','SE03']),
      '| SI sum = S000:', bool((odsi[['SI01','SI02','SI03']].sum(axis=1) == odsi.S000).all()))

wac = pd.read_csv('data/raw/lodes/oh_wac_S000_JT00_2019.csv.gz', usecols=['w_geocode']+list(CNS), dtype={'w_geocode':str})
wac['wp'] = wac.w_geocode.map(blk).fillna('9999999')
g = wac.groupby('wp')[list(CNS)].sum()
def share(cols):
    c = [k for k in cols if k in used]
    num = sum(g[k]*sc[CNS[k]] for k in c); den = g[c].sum(axis=1)
    state = sum(g[k].sum()*sc[CNS[k]] for k in c) / g[c].sum().sum()
    return (num/den.replace(0, np.nan)), state
place_tw, state_all = share(list(CNS))
si_tw, si_state = {}, {}
for s, cols in SUPER.items():
    si_tw[s], si_state[s] = share(cols)
print('statewide job-weighted DN share: all', round(state_all,4), {k: round(v,4) for k, v in si_state.items()})
tw_tab = pd.DataFrame({'tw_place':place_tw, **{f'tw_{s}':si_tw[s] for s in SUPER}, **{f'jobs_{s}':g[[k for k in SUPER[s] if k in used]].sum(axis=1) for s in SUPER}})
tw_tab.to_csv('output/ohio/place_teleworkability_si_2019.csv', index_label='stplc')

def flow_tw(d):
    x = d[['hp','wp']].merge(odsi[['hp','wp','SI01','SI02','SI03']], on=['hp','wp'], how='left')
    num = np.zeros(len(x)); fb = np.zeros(len(x))
    for s in SUPER:
        t = x.wp.map(si_tw[s]); miss = t.isna() & (x[s] > 0)
        fb += np.where(miss, x[s], 0); num += x[s].values * t.fillna(si_state[s]).values
    n = x[['SI01','SI02','SI03']].sum(axis=1).values
    return num/n, fb.sum()/n.sum()

def alloc(d, tw):
    e = d.earn.values*tw/100; t_w = d.t_w.values; t_r = d.t_r.fillna(0).values
    taxing = (d.rcls=='taxing').values; unres = d.rcls.str.startswith('unresolved').values
    wl = (e*t_w).sum(); cr = d.cr.values
    cstar = np.where(taxing, np.minimum(t_w, t_r), 0)
    cstar_rng = np.where(taxing|unres, np.minimum(t_w, t_r), 0)
    un = (d.rcls=='unincorporated').values
    return dict(worker=1-(e*cr).sum()/wl, home=(e*cr).sum()/wl, full_credit_worker=1-(e*cstar_rng).sum()/wl,
                untaxed=(e*t_w)[~taxing].sum()/wl, uninc=(e*t_w)[un].sum()/wl, notax_muni=(e*t_w)[~taxing&~un].sum()/wl,
                rate_above=(e*np.maximum(t_w-t_r,0))[taxing].sum()/wl, incomplete=(e*(cstar-cr)).sum()/wl,
                tele_earn_bn=(d.earn.values*tw).sum()/1e9, tele_jobs=(d.S000.values*tw).sum(), loss_bn=wl/1e9,
                uninc_share_tele_earn=(d.earn.values*tw)[un].sum()/(d.earn.values*tw).sum(),
                tw_uninc=(d.S000.values*tw)[un].sum()/d.S000.values[un].sum(),
                tw_taxing_res=(d.S000.values*tw)[taxing].sum()/d.S000.values[taxing].sum())

bands = [('base 800/2300/6000',{'SE01':800,'SE02':2300,'SE03':6000}),('low 600/2000/4500',{'SE01':600,'SE02':2000,'SE03':4500}),('high 1000/2800/9000',{'SE01':1000,'SE02':2800,'SE03':9000})]
rows = []
for (lab, W), tm, u in itertools.product(bands, ['DN','uniform'], ['low','high']):
    _, _, d = run(W, tm, u)
    d = d.reset_index(drop=True)
    old = alloc(d, d.tw.values)
    if tm == 'DN':
        tw_new, fb = flow_tw(d)
    else:
        tw_new, fb = d.tw.values, 0.0
    new = alloc(d, tw_new)
    rows.append(dict(bands=lab, teleworkability=tm, unknowns=u, fallback_job_share=fb,
                     **{f'old_{k}':v for k, v in old.items()}, **{f'new_{k}':v for k, v in new.items()}))
R = pd.DataFrame(rows)
R.to_csv('output/ohio/allocation_flow_industry_sensitivity.csv', index=False)
b = R.iloc[0]
keys = ['worker','home','untaxed','uninc','notax_muni','rate_above','incomplete','full_credit_worker','loss_bn','tele_earn_bn','tele_jobs','uninc_share_tele_earn','tw_uninc','tw_taxing_res']
T = pd.DataFrame({'old':[b[f'old_{k}'] for k in keys],'new_si':[b[f'new_{k}'] for k in keys]}, index=keys)
print('\nbase case (800/2300/6000, DN, unknowns low); fallback job share', round(b.fallback_job_share,5))
print(T.to_string(float_format=lambda v: f'{v:,.4f}'))
print('\n12-variant worker share: old', round(R.old_worker.min(),4), '-', round(R.old_worker.max(),4), '| new', round(R.new_worker.min(),4), '-', round(R.new_worker.max(),4))
print('12-variant full-credit worker share: old', round(R.old_full_credit_worker.min(),4), '-', round(R.old_full_credit_worker.max(),4), '| new', round(R.new_full_credit_worker.min(),4), '-', round(R.new_full_credit_worker.max(),4))
print(R[['bands','teleworkability','unknowns','old_worker','new_worker','old_full_credit_worker','new_full_credit_worker']].round(4).to_string(index=False))
T.to_csv('output/ohio/allocation_flow_industry_base.csv', index_label='quantity')

_, _, d = run(bands[0][1], 'DN', 'low'); d = d.reset_index(drop=True)
tw_new, _ = flow_tw(d)
taxing = (d.rcls=='taxing').values; t_w = d.t_w.values; t_r = d.t_r.fillna(0).values
cstar = np.where(taxing, np.minimum(t_w, t_r), 0); cr = d.cr.values; jobs = d.S000.values
below = taxing & (cr < cstar-1e-12); rateonly = taxing & ~below & (t_w > t_r+1e-12); nosave = taxing & ~below & ~rateonly
print('\nPanel C (raw jobs; rule: untaxed home first, then credit below benchmark, then work rate above home rate, else no saving)')
for nm, m in [('home levies no tax',~taxing),('credit below benchmark',below),('only work rate above home rate',rateonly),('no saving',nosave)]:
    print(f'  {nm}: {int(jobs[m].sum()):,}  ({100*jobs[m].sum()/jobs.sum():.1f}%)  tele-weighted old {100*(jobs*d.tw.values)[m].sum()/(jobs*d.tw.values).sum():.1f}% new {100*(jobs*tw_new)[m].sum()/(jobs*tw_new).sum():.1f}%')
both = below & (t_w > t_r+1e-12)
print('  flows meeting both conditions: jobs', f'{int(jobs[both].sum()):,}', '-> all counted as credit below benchmark')

rac = pd.read_csv('data/raw/lodes/oh_rac_S000_JT00_2019.csv.gz', usecols=['h_geocode']+list(CNS), dtype={'h_geocode':str})
rac['hp'] = rac.h_geocode.map(blk).fillna('9999999'); rac['cls'] = rac.hp.map(C).fillna(rac.hp.map(classify))
rg = rac.groupby('cls')[used].sum()
rt = pd.DataFrame({'jobs':rg.sum(axis=1), 'tele_share':sum(rg[k]*sc[CNS[k]] for k in used)/rg.sum(axis=1)})
print('\nRAC 2019 teleworkable share of jobs held by residents, by residence class (19 sectors):'); print(rt.round(4).to_string())
cm = pd.DataFrame({'cls':d.rcls, 'S000':jobs, 'old':jobs*d.tw.values, 'new':jobs*tw_new}).groupby('cls').sum()
cm['old_share'] = cm.old/cm.S000; cm['new_share'] = cm.new/cm.S000
print('\nCommuters into taxing workplaces, teleworkable job share by residence class:'); print(cm[['S000','old_share','new_share']].round(4).to_string())
rt.to_csv('output/ohio/rac_tele_by_class_2019.csv', index_label='cls'); cm.to_csv('output/ohio/commuter_tele_by_class_2019.csv', index_label='cls')
