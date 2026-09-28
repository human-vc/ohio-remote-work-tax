import pandas as pd,numpy as np,os
xw=pd.read_csv('data/raw/lodes/oh_xwalk.csv.gz',usecols=['tabblk2020','stplc'],dtype=str)
b2p=dict(zip(xw.tabblk2020,xw.stplc.fillna('')))
cns=[f'CNS{i:02d}' for i in range(1,21)]
rac=pd.read_csv('data/raw/lodes/oh_rac_S000_JT00_2019.csv.gz',dtype={'h_geocode':str},usecols=['h_geocode','C000','CE01','CE02','CE03']+cns)
rac['stplc']=rac.h_geocode.map(b2p).fillna('')
P=rac[rac.stplc!=''].groupby('stplc')[['C000','CE01','CE02','CE03']+cns].sum()
naics=['11','21','22','23','31-33','42','44-45','48-49','51','52','53','54','55','56','61','62','71','72','81','99']
t=pd.read_csv('data/ohio/NAICS_workfromhome.csv',dtype={'NAICS':str}).set_index('NAICS').teleworkable_emp
w=np.array([t[n] for n in naics])
C=pd.DataFrame(index=P.index)
C['res_tele']=(P[cns].values*w).sum(1)/P.C000
C['res_high_earn']=P.CE03/P.C000
C['res_goods']=P[['CNS01','CNS02','CNS04','CNS05']].sum(1)/P.C000
C['res_trade_transport']=P[['CNS03','CNS06','CNS07','CNS08']].sum(1)/P.C000
C['res_workers_rac']=P.C000
C.to_csv('output/ohio/controls_2019.csv',index_label='stplc')
print('places',len(C)); print(C.describe().round(3).to_string())
