import pandas as pd, numpy as np
exec(open('scripts/ohio/allocation.py').read().split("res=[]")[0])
out = []
s, us, d = run({'SE01':800,'SE02':2300,'SE03':6000}, 'DN', 'low')
E0 = (d.earn*d.tw/100).values
tw_, tr_ = d.t_w.values, d.t_r.fillna(0).values
fac_ = (d.hp.map(fac)/100).fillna(0).values; cap_ = d.hp.map(cap).fillna(0).values
taxing = (d.rcls=='taxing').values
def credit(f, c): return np.where(taxing, np.minimum(f*np.minimum(tw_, c), tr_), 0.0)
W = E0*taxing
for nm, cr in [('actual', credit(fac_, cap_)), ('full', credit(np.ones_like(fac_), tr_)), ('half', credit(0.5*np.ones_like(fac_), tr_)), ('none', np.zeros_like(tw_))]:
    out.append(('township_advantage_commuting', nm, (W*(tr_-cr)).sum()/W.sum()))
    out.append(('township_advantage_remote', nm, (W*tr_).sum()/W.sum()))
rp = np.maximum(tw_-tr_, 0)+tr_-tw_
out.append(('township_advantage_commuting', 'residence_priority', (W*rp).sum()/W.sum()))
out.append(('township_advantage_remote', 'residence_priority', (W*tr_).sum()/W.sum()))
cr = credit(fac_, cap_); cstar = np.where(taxing, np.minimum(tw_, tr_), 0)
un = (d.rcls=='unincorporated').values
for k in [0.4, 0.5, 0.68, 0.8, 0.95, 1.0, 1.2, 1.5]:
    e = E0*np.where(un, k, 1); wl = (e*tw_).sum()
    out.append(('stress_worker_share_actual', k, 100*(1-(e*cr).sum()/wl)))
    out.append(('stress_worker_share_full_credit', k, 100*(1-(e*cstar).sum()/wl)))
xw = pd.read_csv('data/raw/lodes/oh_xwalk.csv.gz', usecols=['tabblk2020','stplc'], dtype=str); b2p = dict(zip(xw.tabblk2020, xw.stplc.fillna('')))
tele = pd.read_csv('output/ohio/place_teleworkability_2019.csv'); tmap = dict(zip(tele.stplcname, tele.teleworkable_share_DN)); pn = dict(zip(pl.stplc, pl.PLACENAME+', OH'))
Wb = {'SE01':800,'SE02':2300,'SE03':6000}
d['b'] = d.earn*d.tw/100
L_in = (d.b*d.t_w).sum()
a = pd.read_csv('data/raw/lodes/oh_od_aux_JT00_2019.csv.gz', dtype={'w_geocode':str,'h_geocode':str})
a['wp'] = a.w_geocode.map(b2p).fillna(''); a['earn'] = sum(a[k]*v for k, v in Wb.items())*12
a['wcls'] = a.wp.map(C); a = a[a.wcls=='taxing'].copy()
a['t_w'] = a.wp.map(rate); a['tw'] = a.wp.map(lambda p: tmap.get(pn.get(p,''), np.nan)).fillna(d.tw.mean())
a['L'] = a.earn*a.tw/100*a.t_w
L_out = a.L.sum()
G_in = (d.b*d.cr).sum()
out.append(('out_of_state', 'share_of_potential_loss', L_out/(L_in+L_out)))
out.append(('out_of_state', 'worker_share_none_to_home', 1-G_in/(L_in+L_out)))
out.append(('out_of_state', 'worker_share_all_to_home', 1-(G_in+L_out)/(L_in+L_out)))
tp = pd.Index([p for p, c in C.items() if c=='taxing'])
r = rate.reindex(tp); f = fac.reindex(tp); c = cap.reindex(tp)
unk = f.isna()|c.isna()
out += [('schedule', 'taxing_places', len(tp)), ('schedule', 'rate_min', r.min()), ('schedule', 'rate_median', r.median()), ('schedule', 'rate_max', r.max()),
        ('schedule', 'credit_unknown', unk.sum()), ('schedule', 'credit_full', ((f==100)&~unk).sum()),
        ('schedule', 'credit_partial', ((f>0)&(f<100)&~unk).sum()), ('schedule', 'credit_none', ((f==0)&~unk).sum()),
        ('schedule', 'full_credit_cap_below_rate', ((c<r)&(f==100)&~unk).sum()),
        ('schedule', 'rita_administered', (Sc.reindex(tp).admin=='RITA').sum())]
pd.DataFrame(out, columns=['measure','case','value']).to_csv('output/ohio/allocation_details.csv', index=False)
print(pd.DataFrame(out, columns=['measure','case','value']).to_string(index=False))
