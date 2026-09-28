import pandas as pd,numpy as np,re,os
def norm(x): return re.sub(r'\s+',' ',re.sub(r'\s*\([^)]*\)','',str(x)).lower().replace('.','').replace('saint ','st ')).strip()
pl=pd.read_csv('data/ohio/st39_places.txt',sep='|',dtype=str); pl['k']=pl.PLACENAME.str.replace(r' (city|village)$','',regex=True).map(norm); pl['stplc']='39'+pl.PLACEFP
P=pl.drop_duplicates('k').set_index('k')
E=pd.read_csv('output/ohio/exposure_2019.csv',dtype={'hp':str}).set_index('hp')
B=pd.read_csv('data/ohio/baseline_schedule_2019_12_31.csv'); B['stplc']=B.member.map(norm).map(P.stplc)
L=pd.read_csv('data/ohio/rita_rates_v2_long.csv'); L['stplc']=L.member.map(norm).map(P.stplc)
S=E[(E.admin=='RITA')&(E.cls.isin(['city','village']))].copy()
sy=B.set_index('stplc').rita_start.pipe(pd.to_datetime,errors='coerce')
S=S[S.index.map(lambda i: pd.notna(sy.get(i)) and sy.get(i)<=pd.Timestamp('2015-01-01'))]
rc=pd.read_csv('data/ohio/rita_member_collections_2016_2025.csv'); rc['stplc']=rc.member.map(norm).map(P.stplc)
p=rc[rc.year.between(2016,2019)].pivot_table(index='stplc',columns='year',values='net_collections',aggfunc='sum')
S=S[S.index.isin(p[(p>0).all(axis=1)].index)]
def changed(field):
    g=L[(L.field==field)&L.year.between(2016,2024)]
    v=g.assign(v=pd.to_numeric(g.value_end,errors='coerce')).groupby('stplc').agg(n=('v','nunique'),split=('split','max'))
    return set(v[(v.n>1)|(v.split>0)].index)
S=S[~S.index.isin(changed('Credit Factor')|changed('Credit Rate')|changed('Tax Rate'))]
print('before credit filter',len(S),'| zero credit',(S.credit_factor==0).sum())
S['lrw']=np.log(S.resident_workers)
pos=S[S.credit_factor>0]; lo,hi=pos.lrw.quantile([.01,.99])
S=S[S.lrw.between(lo,hi)]
S['county']=S.index.map(lambda i: pl.set_index('stplc').COUNTIES.get(i,'').split('~~~')[0])
C=pd.read_csv('output/ohio/controls_2019.csv',dtype={'stplc':str}).set_index('stplc')
cb=pd.read_csv('data/ohio/oh_county_cbsa.csv',dtype=str); m=dict(zip(cb.county,cb['CBSA Code']))
S['metro']=S.county.map(m).fillna('nonCBSA_'+S.county); S=S.join(C)
S['Loss']=S.workplace_loss_index.fillna(0)/S.rev2019
od=pd.read_csv('output/ohio/od_place_2019_bands.csv.gz',dtype={'hp':str,'wp':str})
Sc=pd.read_csv('output/ohio/schedule_2019_12_31.csv',dtype={'stplc':str}).set_index('stplc')
tele=pd.read_csv('output/ohio/place_teleworkability_2019.csv')
tmap=dict(zip(tele.stplcname,tele.teleworkable_share_DN)); plname=dict(zip(pl.stplc,pl.PLACENAME+', OH'))
od['earn']=sum(od[k]*v for k,v in {'SE01':800,'SE02':2300,'SE03':6000}.items())*12
od['t_w']=od.wp.map(Sc.tax_rate).fillna(0); od['cap']=od.hp.map(Sc.credit_cap); od['t_r']=od.hp.map(Sc.tax_rate)
od['tw']=od.wp.map(lambda q: tmap.get(plname.get(q,''),np.nan)); od['tw']=od.tw.fillna(od.tw.mean())
x=od[(od.hp!='')&(od.hp!=od.wp)].copy()
x['pot_rate']=np.minimum(np.minimum(x.t_w,x.cap.where(x.cap>0,x.t_r)),x.t_r)
S=S.join((x.earn*x.tw*x.pot_rate/100).groupby(x.hp).sum().rename('pot'))
S['Potential']=S.pot/S.rev2019
S['Gain']=S.g_earn/S.rev2019
S['zero']=(S.credit_factor==0).astype(int)
old=pd.read_csv('output/revenue/sample_primary_with_controls.csv',dtype={'stplc':str}).set_index('stplc')
print('extended',len(S),'| positive',(S.zero==0).sum(),'(frozen 121 contained:',S.index.isin(old.index).sum(),') | zero',S.zero.sum())
print(S.groupby('zero')[['Potential','Gain','res_tele','res_high_earn','lrw','Loss','tax_rate']].mean().round(3).T)
S[(S.zero==1)|S.index.isin(old.index)].to_csv('output/revenue/sample_nocredit_extended.csv',index_label='stplc')
S[S.zero==1].assign(Gain=lambda z:z.Potential).to_csv('output/revenue/sample_nocredit_zero.csv',index_label='stplc')
