import pandas as pd,numpy as np,os
od=pd.read_csv('output/ohio/od_place_2019_bands.csv.gz',dtype={'hp':str,'wp':str})
Sc=pd.read_csv('output/ohio/schedule_2019_12_31.csv',dtype={'stplc':str}).set_index('stplc')
tele=pd.read_csv('output/ohio/place_teleworkability_2019.csv')
pl=pd.read_csv('data/ohio/st39_places.txt',sep='|',dtype=str); pl['stplc']='39'+pl.PLACEFP
tmap=dict(zip(tele.stplcname,tele.teleworkable_share_DN)); plname=dict(zip(pl.stplc,pl.PLACENAME+', OH'))
W={'SE01':800,'SE02':2300,'SE03':6000}; od['earn']=sum(od[k]*v for k,v in W.items())*12
od['t_w']=od.wp.map(Sc.tax_rate).fillna(0); od['cap']=od.hp.map(Sc.credit_cap); od['t_r']=od.hp.map(Sc.tax_rate)
od['tw']=od.wp.map(lambda p: tmap.get(plname.get(p,''),np.nan)); od['tw']=od.tw.fillna(od.tw.mean())
x=od[(od.hp!='')&(od.hp!=od.wp)].copy()
x['pot_rate']=np.minimum(np.minimum(x.t_w,x.cap.where(x.cap>0,x.t_r)),x.t_r)
P=(x.earn*x.tw*x.pot_rate/100).groupby(x.hp).sum().rename('pot_gain_dollars')
S=pd.read_csv('output/revenue/sample_primary_with_controls.csv',dtype={'stplc':str}).set_index('stplc')
S=S.join(P)
S['Potential']=S.pot_gain_dollars/S.rev2019
S['credit_frac']=S.credit_factor/100
print('check Gain ~ credit_frac x Potential: corr',round(np.corrcoef(S.Gain,S.credit_frac*S.Potential)[0,1],4))
S['full']=(S.credit_factor==100).astype(int)
cols=['Potential','res_tele','res_high_earn','res_goods','res_trade_transport','lrw','out_share' if 'out_share' in S else 'lrw','Loss']
print('\nBALANCE full vs partial credit (primary sample):')
b=S.groupby('full')[['Potential','res_tele','res_high_earn','res_goods','res_trade_transport','lrw','Loss']].mean().T
b['std_diff']=(b[1]-b[0])/S[['Potential','res_tele','res_high_earn','res_goods','res_trade_transport','lrw','Loss']].std()
print(b.round(3).to_string()); print('counts:',S.full.value_counts().to_dict())
mx=S.groupby(['metro','full']).size().unstack(fill_value=0); both=mx[(mx[0]>0)&(mx[1]>0)]
print('\nmetros containing BOTH full and partial places:',len(both),'| places in them:',int(both.values.sum()),'| partial places in them:',int(both[0].sum()))
print(both.to_string())
X=['Potential','res_tele','res_high_earn','res_goods','res_trade_transport','lrw']
T=S[S.metro.isin(both.index)]
D=pd.get_dummies(T.metro).astype(float).values
Z=np.column_stack([T[X].values,D]); r=T.credit_frac.values-Z@np.linalg.lstsq(Z,T.credit_frac.values,rcond=None)[0]
print('credit_frac residual sd within those metros after controls:',round(r.std(),3),'raw sd',round(T.credit_frac.std(),3))
S.to_csv('output/revenue/sample_with_potential.csv',index_label='stplc')
