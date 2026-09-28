import pandas as pd,numpy as np,os
exec(open('scripts/ohio/allocation.py').read().split("res=[]")[0])
s,us,d=run({'SE01':800,'SE02':2300,'SE03':6000},'DN','low')
d=d[d.cr.notna()].copy()
E=d.earn*d.tw/100
tw_,tr_=d.t_w.values,d.t_r.fillna(0).values
fac_=(d.hp.map(fac)/100).fillna(0).values; cap_=d.hp.map(cap).fillna(0).values
taxing=(d.rcls=='taxing').values
def credit(f,c): return np.where(taxing,np.minimum(f*np.minimum(tw_,c),tr_),0.0)
scen={
 'Actual 2019 rules':('credit',credit(fac_,cap_)),
 'All full credit (factor 100%, cap = own rate)':('credit',credit(np.ones_like(fac_),tr_)),
 'All 50% credit (cap = own rate)':('credit',credit(0.5*np.ones_like(fac_),tr_)),
 'No credit anywhere':('credit',np.zeros_like(tw_)),
 'Residence-priority allocation':('resprio',None),
}
rows=[]
for name,(kind,cr) in scen.items():
    if kind=='credit':
        work_pre=tw_; home_pre=np.where(taxing,tr_-cr,0)
    else:
        work_pre=np.maximum(tw_-np.where(taxing,tr_,0),0); home_pre=np.where(taxing,tr_,0)
    home_post=np.where(taxing,tr_,0); work_post=np.zeros_like(tw_)
    pre_total=(E*(work_pre+home_pre)).sum(); post_total=(E*(home_post)).sum()
    d_work=(E*(work_post-work_pre)).sum(); d_home=(E*(home_post-home_pre)).sum()
    rows.append(dict(scenario=name,
        pre_collections_bn=pre_total/1e9, post_collections_bn=post_total/1e9,
        workplace_change_bn=d_work/1e9, residence_change_bn=d_home/1e9, worker_saving_bn=(pre_total-post_total)/1e9,
        pre_burden_pct=100*pre_total/E.sum()/100, post_burden_pct=100*post_total/E.sum()/100,
        share_of_workplace_loss_to_residences=(d_home/-d_work) if d_work<0 else np.nan))
R=pd.DataFrame(rows)
pd.set_option('display.width',250)
print(R.round(3).to_string(index=False))
R.to_csv('output/ohio/credit_counterfactuals.csv',index=False)
