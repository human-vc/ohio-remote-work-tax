import pandas as pd, numpy as np, re
def norm(x): return re.sub(r'\s+',' ',re.sub(r'\s*\([^)]*\)','',str(x)).lower().replace('.','').replace('saint ','st ').replace('mt ','mount ')).strip()
pl=pd.read_csv('data/ohio/st39_places.txt',sep='|',dtype=str); pl['stplc']='39'+pl.PLACEFP
pl['k']=pl.PLACENAME.str.replace(r' (city|village)$','',regex=True).map(norm)
inc=pl[pl.PLACENAME.str.contains(r' (city|village)$')].drop_duplicates('k').set_index('k')
A=pd.read_csv('data/ohio/aos_city_income_tax_panel.csv'); A['k']=A.entity.str.replace(r'^City of ','',regex=True).map(norm); A['stplc']=A.k.map(inc.stplc)
log=[('Auditor city entities',A.entity.nunique())]
A=A.dropna(subset=['stplc']); log.append(('matched to 2020 place code',A.stplc.nunique()))
A=A[A.fy.between(2016,2024)]
g=A.groupby('stplc').agg(n=('fy','nunique'),pos=('gw_income_tax',lambda v:(v>0).all()),nb=('basis','nunique'))
keep=g[(g.n==9)&g.pos&(g.nb==1)].index; log.append(('all 9 years, positive revenue, one accounting basis',len(keep)))
E=pd.read_csv('output/ohio/exposure_2019.csv',dtype={'hp':str}).set_index('hp')
S=E[E.index.isin(keep)].copy(); log.append(('with 2019 exposure',len(S)))
F=pd.read_csv('data/ohio/finder_muni_20200711195940.csv',header=None,names=['frm','to','code','name','rate'],dtype=str)
F['stplc']='39'+F.code
fr=F[(F.to.astype(int)>=20160101)&(F.frm.astype(int)<=20241231)].groupby('stplc').rate.nunique()
rl=pd.read_csv('data/ohio/rita_rates_v2_long.csv'); rl['stplc']=rl.member.map(norm).map(inc.stplc)
def changed(field):
    q=rl[(rl.field==field)&rl.year.between(2016,2024)]
    v=q.assign(v=pd.to_numeric(q.value_end,errors='coerce')).groupby('stplc').agg(n=('v','nunique'),split=('split','max'))
    return set(v[(v.n>1)|(v.split>0)].index)
rate_ch=set(fr[fr>1].index)|changed('Tax Rate')
S=S[~S.index.isin(rate_ch)]; log.append(('no rate change (Finder to mid-2020; RITA tables to 2024)',len(S)))
cc=pd.read_csv('data/ohio/credit_changes_dated.csv'); cc['stplc']=cc.member.map(norm).map(inc.stplc)
cc=cc[pd.to_datetime(cc.effective_date,errors='coerce').between('2016-01-01','2024-12-31')]
cr_ch=set(cc.stplc.dropna())|changed('Credit Factor')|changed('Credit Rate')
S=S[~S.index.isin(cr_ch)]; log.append(('no documented credit change 2016-2024',len(S)))
S=S[S.credit_factor>0]; log.append(('positive credit factor',len(S)))
a19=A[A.fy==2019].groupby('stplc').gw_income_tax.sum()
S['rev_aos19']=a19.reindex(S.index)
S['Gain']=S.g_earn/S.rev_aos19; S['Loss']=S.workplace_loss_index.fillna(0)/S.rev_aos19
S['lrw']=np.log(S.resident_workers); lo,hi=S.lrw.quantile([.01,.99]); S=S[S.lrw.between(lo,hi)]; log.append(('drop 1st/99th pct resident workers',len(S)))
S['county']=S.index.map(lambda i: pl.set_index('stplc').COUNTIES.get(i,'').split('~~~')[0])
cb=pd.read_csv('data/ohio/oh_county_cbsa.csv',dtype=str).set_index('county')['CBSA Code']
S['metro']=S.county.map(lambda c: cb.get(c,'nonCBSA_'+c))
C=pd.read_csv('output/ohio/controls_2019.csv',dtype={'stplc':str}).set_index('stplc')
S=S.join(C[['res_tele','res_high_earn','res_goods','res_trade_transport']])
nonrita=(S.admin!='RITA').sum()
for a,b in log: print(f'{b:5d}  {a}')
print('non-RITA cities in final sample:',nonrita,'| big six present:',[n for n in ['columbus','cleveland','cincinnati','toledo','akron','dayton'] if n in S.name.str.lower().tolist()])
print('counties',S.county.nunique(),'metros',S.metro.nunique(),'| missing controls',S[['res_tele']].isna().sum().item())
print(S[['Gain','Loss']].describe().round(3).to_string())
S.index.name='stplc'; S.to_csv('output/revenue/sample_aos.csv')
A[A.stplc.isin(S.index)][['stplc','fy','gw_income_tax']].to_csv('output/revenue/aos_outcome.csv',index=False)
b=pd.read_csv('output/revenue/sample_primary_with_controls.csv',dtype={'stplc':str}).set_index('stplc')
com=b.index.intersection(S.index); print('common',len(com),'| agency members not in primary',((S.admin=='RITA')&~S.index.isin(com)).sum())
b.loc[com].to_csv('output/revenue/sample_common.csv')
