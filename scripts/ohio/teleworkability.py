import pandas as pd, os
dn=pd.read_csv('data/ohio/NAICS_workfromhome.csv',dtype={'NAICS':str})
cns={'CNS01':'11','CNS02':'21','CNS03':'22','CNS04':'23','CNS05':'31-33','CNS06':'42','CNS07':'44-45','CNS08':'48-49','CNS09':'51','CNS10':'52','CNS11':'53','CNS12':'54','CNS13':'55','CNS14':'56','CNS15':'61','CNS16':'62','CNS17':'71','CNS18':'72','CNS19':'81','CNS20':'92'}
sc=dict(zip(dn.NAICS,dn.teleworkable_emp))
miss=[v for v in cns.values() if v not in sc]; print('DN codes missing:',miss, 'available:',list(sc)[:25])
w=pd.read_csv('data/raw/lodes/oh_wac_S000_JT00_2019.csv.gz',dtype={'w_geocode':str})
xw=pd.read_csv('data/raw/lodes/oh_xwalk.csv.gz',usecols=['tabblk2020','stplcname'],dtype=str)
w=w.merge(xw,left_on='w_geocode',right_on='tabblk2020',how='left')
g=w.groupby('stplcname')[list(cns)].sum()
num=sum(g[k]*sc.get(v,float('nan')) for k,v in cns.items() if v in sc); den=g[[k for k,v in cns.items() if v in sc]].sum(axis=1)
out=pd.DataFrame({'jobs':g.sum(axis=1),'teleworkable_share_DN':num/den}).reset_index()
out.to_csv('output/ohio/place_teleworkability_2019.csv',index=False)
S=['Columbus','Cleveland','Cincinnati','Dayton','Akron','Toledo','Dublin','Westerville','Hilliard','Mason','Solon','Upper Arlington','Worthington','Bexley']
print(out[out.stplcname.isin([s+' city, OH' for s in S])].round(3).to_string(index=False))
