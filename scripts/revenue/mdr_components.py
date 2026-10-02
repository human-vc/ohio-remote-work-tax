import pandas as pd,numpy as np
d=pd.read_csv('data/ohio/rita_mdr_cash_ytd.csv')
cur=d[d.year==d.report].merge(d[d.year<d.report],on=['muni','year'],suffixes=('','_later'))
print('overlapping member-years',len(cur),'max abs difference',max((cur[c]-cur[c+'_later']).abs().max() for c in ['total','wh','ind','np']))
d=d.sort_values('report').groupby(['muni','year']).last().reset_index()
b=d[d.year==2019].set_index('muni').total
for c in ['total','wh','ind','np']: d[c+'_s']=d[c]/d.muni.map(b)
d['city']=d.muni.str.title()
d.rename(columns={'wh':'withholding','ind':'individual','np':'net_profit'})[['city','year','total','withholding','individual','net_profit','wh_tax','ind_tax','total_s','wh_s','ind_s','np_s']].to_csv('output/revenue/components_mdr.csv',index=False)
rc=pd.read_csv('data/ohio/rita_member_collections_2016_2025.csv')
k=lambda s: s.str.lower().str.replace(r'[^a-z]','',regex=True)
m=d.assign(k=k(d.muni)).merge(rc.assign(k=k(rc.member)),on=['k','year'])
print((m.total/m.net_collections).groupby(m.year).median().round(3).to_string())
