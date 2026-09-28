import pandas as pd
a=pd.read_csv('data/ohio/acs5_2023_b08301_oh.dat',sep='|',dtype=str)
a['tot']=a.B08301_E001.astype(int); a['wfh']=a.B08301_E021.astype(int)
cs=a[a.GEO_ID.str.startswith('0600000')]; pl=a[a.GEO_ID.str.startswith('1600000')].copy()
pl['PLACEFP']=pl.GEO_ID.str[-5:]
P=pd.read_csv('data/ohio/st39_places.txt',sep='|',dtype=str)
pl=pl.merge(P[['PLACEFP','PLACENAME']],on='PLACEFP',how='left')
inc=pl[pl.PLACENAME.str.contains(r' (city|village)$',na=False)]
T,W=cs.tot.sum(),cs.wfh.sum(); it,iw=inc.tot.sum(),inc.wfh.sum(); ut,uw=T-it,W-iw
r=pd.DataFrame([('incorporated',it,iw,100*iw/it),('unincorporated',ut,uw,100*uw/ut)],columns=['territory','workers','wfh','wfh_pct'])
r.loc[2]=['ratio',None,None,(uw/ut)/(iw/it)]
r.to_csv('output/ohio/acs_township_wfh.csv',index=False); print(r.to_string(index=False))
