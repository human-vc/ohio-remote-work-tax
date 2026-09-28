import pandas as pd,numpy as np,sys
W={'SE01':800,'SE02':2300,'SE03':6000}
import csv
rows=list(csv.reader(open(sys.argv[1] if len(sys.argv)>1 else 'data/michigan/mi_city_rates_2019_verified.csv')))
R=pd.DataFrame([[r[0],r[1],r[2],r[-1]] for r in rows[1:]],columns=['city','resident_rate','nonresident_rate','status'])
R=R[R.status.str.lower().eq('verified')][['city','resident_rate','nonresident_rate']]
R=pd.concat([R,pd.DataFrame([['Detroit',2.4,1.2],['East Lansing',1.0,0.5]],columns=R.columns)]).drop_duplicates('city',keep='last')
for c in ['resident_rate','nonresident_rate']:
    R[c]=pd.to_numeric(R[c].astype(str).str.rstrip('%')); R[c]=np.where(R[c]<0.2,R[c]*100,R[c])
names=pd.read_csv('output/states/mi_place_names.csv',dtype=str).set_index('stplc').iloc[:,0]
n2p={v.replace(' city, MI',''):k for k,v in names.items() if isinstance(v,str) and v.endswith(' city, MI')}
R['stplc']=R.city.map(n2p); miss=R[R.stplc.isna()].city.tolist()
print('MI taxing cities used:',len(R.dropna(subset=['stplc'])),'| unmatched:',miss)
R=R.dropna(subset=['stplc']).set_index('stplc')
od=pd.read_csv('output/states/mi_od_place_2019_bands.csv.gz',dtype={'hp':str,'wp':str}).fillna({'hp':'','wp':''})
tele=pd.read_csv('output/states/mi_place_tele_2019.csv',dtype={'stplc':str}).set_index('stplc').tele
od['earn']=sum(od[k]*v for k,v in W.items())*12; od['tw']=od.wp.map(tele).fillna(tele.mean())
mi=od[(od.hp!=od.wp)&od.wp.isin(R.index)].copy()
mi['t_w']=mi.wp.map(R.resident_rate); mi['n_w']=mi.wp.map(R.nonresident_rate)
mi['t_r']=mi.hp.map(R.resident_rate).fillna(0); mi['n_r']=mi.hp.map(R.nonresident_rate).fillna(0); mi['taxing_home']=mi.hp.isin(R.index)
g={}; exec(open('scripts/ohio/allocation.py').read().split("res=[]")[0],g)
s_oh,_,oh=g['run'](W,'DN','low'); oh=oh[oh.cr.notna()].copy()
oh['taxing_home']=oh.rcls.eq('taxing'); oh['t_r']=np.where(oh.taxing_home,oh.t_r.fillna(0),0.0)
def share(df,work_rate,credit):
    E=df.earn*df.tw/100; L=(E*work_rate).sum(); G=(E*credit).sum(); return 1-G/L, L/1e9
res=[]
res.append(('Ohio','actual rules',*share(oh,oh.t_w,oh.cr)))
res.append(('Michigan','actual rules',*share(mi,mi.n_w,np.where(mi.taxing_home,np.minimum(mi.n_w,mi.n_r),0))))
for name,df,tw_,tr_ in (('Ohio',oh,oh.t_w,oh.t_r),('Michigan',mi,mi.t_w,mi.t_r)):
    th=df.taxing_home.values
    res.append((name,'Regime O (single rate, full credit capped at home rate)',*share(df,tw_,np.where(th,np.minimum(tw_,tr_),0))))
    res.append((name,'Regime M (nonresident half rate, credit capped at home nonresident rate)',*share(df,tw_/2,np.where(th,np.minimum(tw_/2,tr_/2),0))))
T=pd.DataFrame(res,columns=['state','rules','worker_share','workplace_loss_bn'])
for name,df in (('Ohio',oh),('Michigan',mi)):
    E=df.earn*df.tw; print(f'{name}: share of teleworkable commuter earnings into taxing workplaces from untaxed residences = {E[~df.taxing_home].sum()/E.sum():.3f}')
pd.set_option('display.width',200); print(T.round(3).to_string(index=False))
T.to_csv('output/states/oh_mi_comparison.csv',index=False)
E=mi.earn*mi.tw/100; cr=np.where(mi.taxing_home,np.minimum(mi.n_w,mi.n_r),0); tr=np.where(mi.taxing_home,mi.t_r,0)
B=(E*(mi.n_w+tr-cr)).sum(); L=(E*mi.n_w).sum(); G=(E*cr).sum()
Eo=oh.earn*oh.tw/100; Bo=(Eo*(oh.t_w+oh.t_r-oh.cr)).sum(); Lo=(Eo*oh.t_w).sum(); Go=(Eo*oh.cr).sum()
A=pd.DataFrame([('Michigan',B,L,G),('Ohio',Bo,Lo,Go)],columns=['state','before','loss','gain'])
A['tax_before_m']=A.before/1e6; A['exposed_share']=A.loss/A.before; A['net_reduction_share']=(A.loss-A.gain)/A.before
A['revenue_left_per_100']=100*(1-A.net_reduction_share); A['loss_to_govts']=A.gain/A.loss; A['loss_to_workers']=1-A.gain/A.loss
print(A.round(4).to_string(index=False))
A.drop(columns=['before','loss','gain']).to_csv('output/states/oh_mi_accounting.csv',index=False)
