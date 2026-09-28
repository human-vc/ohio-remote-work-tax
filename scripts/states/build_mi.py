import pandas as pd,numpy as np
dn=pd.read_csv('data/ohio/NAICS_workfromhome.csv',dtype={'NAICS':str})
cns={'CNS01':'11','CNS02':'21','CNS03':'22','CNS04':'23','CNS05':'31-33','CNS06':'42','CNS07':'44-45','CNS08':'48-49','CNS09':'51','CNS10':'52','CNS11':'53','CNS12':'54','CNS13':'55','CNS14':'56','CNS15':'61','CNS16':'62','CNS17':'71','CNS18':'72','CNS19':'81','CNS20':'92'}
sc=dict(zip(dn.NAICS,dn.teleworkable_emp))
xw=pd.read_csv('data/raw/lodes/mi_xwalk.csv.gz',usecols=['tabblk2020','stplc','stplcname'],dtype=str)
w=pd.read_csv('data/raw/lodes/mi_wac_S000_JT00_2019.csv.gz',dtype={'w_geocode':str}).merge(xw,left_on='w_geocode',right_on='tabblk2020',how='left')
g=w.groupby('stplc')[list(cns)].sum(); ks=[k for k,v in cns.items() if v in sc]
tele=(sum(g[k]*sc[cns[k]] for k in ks)/g[ks].sum(axis=1)).rename('tele')
tele.to_csv('output/states/mi_place_tele_2019.csv')
b2p=dict(zip(xw.tabblk2020,xw.stplc.fillna('')))
agg={}
for ch in pd.read_csv('data/raw/lodes/mi_od_main_JT00_2019.csv.gz',usecols=['w_geocode','h_geocode','S000','SE01','SE02','SE03'],dtype={'w_geocode':str,'h_geocode':str},chunksize=500_000):
    ch['wp']=ch.w_geocode.map(b2p).fillna(''); ch['hp']=ch.h_geocode.map(b2p).fillna('')
    gg=ch.groupby(['hp','wp'])[['S000','SE01','SE02','SE03']].sum()
    for k,v in zip(gg.index,gg.values):
        a=agg.setdefault(k,np.zeros(4)); a+=v
od=pd.DataFrame([(h,w_,*v) for (h,w_),v in agg.items()],columns=['hp','wp','S000','SE01','SE02','SE03'])
od.to_csv('output/states/mi_od_place_2019_bands.csv.gz',index=False)
names=xw.drop_duplicates('stplc').set_index('stplc').stplcname
pd.Series(names).to_csv('output/states/mi_place_names.csv')
print('MI od pairs',len(od),'jobs',od.S000.sum(),'| places with tele',len(tele))
