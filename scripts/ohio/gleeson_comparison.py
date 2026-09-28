import pandas as pd,numpy as np
exec(open('scripts/ohio/allocation.py').read().split("res=[]")[0])
GA=pd.read_csv('data/ohio/gleeson_andre_2022_pct20.csv').set_index('city').GA_pct20.to_dict()
W={'SE01':800,'SE02':2300,'SE03':6000}
d0=od.copy(); d0['earn']=sum(d0[k]*v for k,v in W.items())*12
tele=pd.read_csv('output/ohio/place_teleworkability_2019.csv'); tmap=dict(zip(tele.stplcname,tele.teleworkable_share_DN)); pn=dict(zip(pl.stplc,pl.PLACENAME+', OH'))
d0['tw']=d0.wp.map(lambda p: tmap.get(pn.get(p,''),np.nan)); d0['tw']=d0.tw.fillna(d0.tw.mean())
d0['t_w']=d0.wp.map(rate).fillna(0); d0['t_r']=d0.hp.map(rate).fillna(0)
f=(d0.hp.map(fac)/100).fillna(0); c=d0.hp.map(cap).fillna(0)
d0['cr']=np.minimum(f*np.minimum(d0.t_w,c),d0.t_r)
name2p={v.replace(' city, OH',''):k for k,v in pn.items() if v.endswith(' city, OH')}
rows=[]
for n,g in GA.items():
    p=name2p.get(n)
    if p is None: continue
    t=rate.get(p,np.nan)
    live_work=d0[(d0.hp==p)&(d0.wp==p)].earn.sum(); inc=d0[(d0.wp==p)&(d0.hp!=p)]; out=d0[(d0.hp==p)&(d0.wp!=p)]
    base=t*(live_work+inc.earn.sum())/100 + ((out.t_r-out.cr)*out.earn/100).sum()
    delta=0.2*((out.earn*out.tw*out.cr/100).sum()-(inc.earn*inc.tw*t/100).sum())
    rows.append((n,g,100*delta/base))
R=pd.DataFrame(rows,columns=['city','GA_pct20','ours_pct20']).set_index('city')
print(R.round(2).to_string()); print('\ncorrelation:',round(R.corr().iloc[0,1],3),'| median ratio ours/GA (losers):',round((R.ours_pct20/R.GA_pct20)[R.GA_pct20<0].median(),2))
print('sign agreement:',int((np.sign(R.GA_pct20)==np.sign(R.ours_pct20)).sum()),'of',len(R))
R.to_csv('output/ohio/gleeson_comparison.csv')
