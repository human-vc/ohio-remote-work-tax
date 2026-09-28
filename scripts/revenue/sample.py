import pandas as pd,numpy as np,re,os
def norm(x): return re.sub(r'\s+',' ',re.sub(r'\s*\([^)]*\)','',str(x)).lower().replace('.','').replace('saint ','st ')).strip()
pl=pd.read_csv('data/ohio/st39_places.txt',sep='|',dtype=str); pl['k']=pl.PLACENAME.str.replace(r' (city|village)$','',regex=True).map(norm); pl['stplc']='39'+pl.PLACEFP
P=pl.drop_duplicates('k').set_index('k')
E=pd.read_csv('output/ohio/exposure_2019.csv',dtype={'hp':str}).set_index('hp')
B=pd.read_csv('data/ohio/baseline_schedule_2019_12_31.csv'); B['stplc']=B.member.map(norm).map(P.stplc)
L=pd.read_csv('data/ohio/rita_rates_v2_long.csv'); L['stplc']=L.member.map(norm).map(P.stplc)
log=[]
S=E[(E.admin=='RITA')&(E.cls.isin(['city','village']))].copy(); log.append(('RITA city/village with exposure',len(S)))
sy=B.set_index('stplc').rita_start.pipe(pd.to_datetime,errors='coerce')
S=S[S.index.map(lambda i: pd.notna(sy.get(i)) and sy.get(i)<=pd.Timestamp('2015-01-01'))]; log.append(('RITA member since <=2015-01-01',len(S)))
rc=pd.read_csv('data/ohio/rita_member_collections_2016_2025.csv'); rc['stplc']=rc.member.map(norm).map(P.stplc)
p=rc[rc.year.between(2016,2019)].pivot_table(index='stplc',columns='year',values='net_collections',aggfunc='sum')
okrev=p[(p>0).all(axis=1)].index
S=S[S.index.isin(okrev)]; log.append(('positive collections every year 2016-2019 (pre-period only)',len(S)))
def changed(field):
    g=L[(L.field==field)&L.year.between(2016,2024)]
    v=g.assign(v=pd.to_numeric(g.value_end,errors='coerce')).groupby('stplc').agg(n=('v','nunique'),split=('split','max'))
    return set(v[(v.n>1)|(v.split>0)].index)
cf=changed('Credit Factor')|changed('Credit Rate'); tr=changed('Tax Rate')
S=S[~S.index.isin(cf)]; log.append(('no credit factor/cap change 2016-2024',len(S)))
rate_changers=S[S.index.isin(tr)].name.tolist()
S=S[~S.index.isin(tr)]; log.append(('no tax-rate change 2016-2024 (default; rate changers kept in robustness)',len(S)))
S=S[S.credit_factor>0]; log.append(('positive credit (primary dose sample)',len(S)))
S['lrw']=np.log(S.resident_workers)
lo,hi=S.lrw.quantile([.01,.99]); S=S[S.lrw.between(lo,hi)]; log.append(('size trimming: 1st/99th pct of 2019 log resident workers',len(S)))
S['county']=S.index.map(lambda i: pl.set_index('stplc').COUNTIES.get(i,'').split('~~~')[0])
for a,b in log: print(f'{b:5d}  {a}')
print('counties in primary sample:',S.county.nunique(),'| places per county median',S.groupby('county').size().median(),'max',S.groupby('county').size().max())
print('rate changers excluded (',len(rate_changers),'):',rate_changers[:40])
S.to_csv('output/revenue/sample_primary.csv',index_label='stplc')
