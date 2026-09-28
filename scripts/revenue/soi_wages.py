import pandas as pd,numpy as np,os
xw=pd.read_csv('data/raw/lodes/oh_xwalk.csv.gz',usecols=['tabblk2020','zcta','stplc'],dtype=str)
rac=pd.read_csv('data/raw/lodes/oh_rac_S000_JT00_2019.csv.gz',usecols=['h_geocode','C000'],dtype={'h_geocode':str})
b=rac.merge(xw,left_on='h_geocode',right_on='tabblk2020',how='left'); b['stplc']=b.stplc.fillna('')
zp=b.groupby(['zcta','stplc']).C000.sum().reset_index()
zp['z_share']=zp.C000/zp.groupby('zcta').C000.transform('sum')
zp['p_share']=zp.C000/zp.groupby('stplc').C000.transform('sum')
W=[]
for y in range(2016,2023):
    s=pd.read_csv(f'data/raw/soi/oh_{str(y)[2:]}.csv',dtype={'zipcode':str})
    s.columns=[c.strip().upper() if c.lower() not in ('zipcode',) else 'zipcode' for c in s.columns]
    s=s[~s.zipcode.isin(['0','00000','99999'])]
    s['zipcode']=s.zipcode.str.zfill(5)
    g=s.groupby('zipcode')[['N1','A00200']].sum()
    g['year']=y; W.append(g.reset_index())
W=pd.concat(W)
m=zp.merge(W,left_on='zcta',right_on='zipcode',how='left')
m['wages_k']=m.A00200*m.z_share
P=m.groupby(['stplc','year']).wages_k.sum().unstack()
purity=zp.assign(x=zp.p_share*zp.z_share).groupby('stplc').x.sum()
matched=zp.merge(W[W.year==2019][['zipcode']],left_on='zcta',right_on='zipcode',how='left',indicator=True)
cov=matched.assign(ok=matched._merge=='both').groupby('stplc').apply(lambda d: (d.p_share*d.ok).sum())
out=P.join(purity.rename('purity')).join(cov.rename('soi_coverage'))
out.to_csv('output/revenue/soi_place_wages_2016_2022.csv',index_label='stplc')
S=pd.read_csv('output/revenue/sample_primary_with_controls.csv',dtype={'stplc':str}).set_index('stplc')
o=out.reindex(S.index)
print('sample places:',len(S),'| with wages all years:',int(o[list(range(2016,2023))].notna().all(1).sum()))
print('purity (share of residents in ZIPs that lie mostly in the place) quantiles:',o.purity.quantile([.1,.25,.5,.75,.9]).round(2).to_dict())
print('SOI coverage of place residents quantiles:',o.soi_coverage.quantile([.1,.5,.9]).round(3).to_dict())
print('places with purity>=0.5:',int((o.purity>=0.5).sum()),'| >=0.3:',int((o.purity>=0.3).sum()))
g=o[list(range(2016,2023))]; print('median resident-wage growth 2019->2022:',round((g[2022]/g[2019]).median(),3))
