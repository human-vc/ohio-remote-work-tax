import runpy,io,contextlib
import pandas as pd,numpy as np
dn=pd.read_csv('data/ohio/NAICS_workfromhome.csv',dtype={'NAICS':str})
cns={'CNS01':'11','CNS02':'21','CNS03':'22','CNS04':'23','CNS05':'31-33','CNS06':'42','CNS07':'44-45','CNS08':'48-49','CNS09':'51','CNS10':'52','CNS11':'53','CNS12':'54','CNS13':'55','CNS14':'56','CNS15':'61','CNS16':'62','CNS17':'71','CNS18':'72','CNS19':'81','CNS20':'92'}
w=pd.read_csv('data/raw/lodes/oh_wac_S000_JT00_2019.csv.gz',dtype={'w_geocode':str})
xw=pd.read_csv('data/raw/lodes/oh_xwalk.csv.gz',usecols=['tabblk2020','stplcname'],dtype=str)
g=w.merge(xw,left_on='w_geocode',right_on='tabblk2020',how='left').groupby('stplcname')[list(cns)].sum()
def place(col,pa=None):
    sc=dict(zip(dn.NAICS,dn[col]))
    if pa is not None: sc['92']=pa
    ks=[k for k,v in cns.items() if v in sc]
    return (sum(g[k]*sc[cns[k]] for k in ks)/g[ks].sum(axis=1)).to_dict()
with contextlib.redirect_stdout(io.StringIO()):
    G=runpy.run_path('scripts/ohio/allocation.py')
od,C,rate,fac,cap,pl=G['od'],G['C'],G['rate'],G['fac'],G['cap'],G['pl']
pn=dict(zip(pl.stplc,pl.PLACENAME+', OH'))
def flows(tmap):
    d=od.copy()
    d['tw']=d.wp.map(lambda p: tmap.get(pn.get(p,''),np.nan)); d['tw']=d.tw.fillna(d.tw.mean())
    d['wcls']=d.wp.map(C); d['rcls']=d.hp.map(C); d=d[(d.hp!=d.wp)&(d.wcls=='taxing')].copy()
    d['t_w']=d.wp.map(rate); d['t_r']=np.where(d.rcls=='taxing',d.hp.map(rate),0.0)
    f=d.hp.map(fac).fillna(0)/100; c=d.hp.map(cap).fillna(0); d['t_r']=d.t_r.fillna(0)
    d['cr']=np.minimum(f*np.minimum(d.t_w,c),d.t_r)
    return d
def result(d,b):
    return 100*(1-(b*d.cr).sum()/(b*d.t_w).sum()),(b*d.t_w).sum()/1e9
earn=lambda d:sum(d[k]*v for k,v in {'SE01':800,'SE02':2300,'SE03':6000}.items())*12
rows=[]
for lab,m in [('baseline',place('teleworkable_emp')),('wage_weighted',place('teleworkable_wage')),('public_admin_zero',place('teleworkable_emp',0.0))]:
    d=flows(m); rows.append((lab,*result(d,earn(d)*d.tw/100)))
d=flows(place('teleworkable_emp'))
T=d.tw*(d.SE01+d.SE02+d.SE03); t3=np.minimum(T,d.SE03); t2=np.minimum(T-t3,d.SE02); t1=T-t3-t2
rows.append(('highest_paid_first',*result(d,(t1*800+t2*2300+t3*6000)*12/100)))
out=pd.DataFrame(rows,columns=['variant','worker_share','workplace_loss_bn'])
out.round(3).to_csv('output/ohio/teleworkability_variants.csv',index=False)
print(out.round(2).to_string(index=False))
