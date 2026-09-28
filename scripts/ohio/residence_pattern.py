import pandas as pd,numpy as np
exec(open('scripts/ohio/allocation.py').read().split("rate=Sc.tax_rate")[0])
xw=pd.read_csv('data/raw/lodes/oh_xwalk.csv.gz',usecols=['tabblk2020','stplc','cty'],dtype=str)
xw['cls']=xw.stplc.fillna('').map(lambda p: C.get(p,'unincorporated') if p else 'unincorporated')
b2=xw.set_index('tabblk2020')[['stplc','cls','cty']]
naics=['11','21','22','23','31-33','42','44-45','48-49','51','52','53','54','55','56','61','62','71','72','81','99']
t=pd.read_csv('data/ohio/NAICS_workfromhome.csv',dtype={'NAICS':str}).set_index('NAICS').teleworkable_emp
w=np.array([t[n] for n in naics]); cns=[f'CNS{i:02d}' for i in range(1,21)]
out={}
for y in (2015,2019,2023):
    r=pd.read_csv(f'data/raw/lodes/oh_rac_S000_JT00_{y}.csv.gz',dtype={'h_geocode':str},usecols=['h_geocode']+cns)
    r=r.join(b2,on='h_geocode')
    r['T']=(r[cns].values*w).sum(1); r['N']=(r[cns].values*(1-w)).sum(1)
    out[y]=r.groupby(['cty','cls','stplc'],dropna=False)[['T','N']].sum()
P=pd.concat(out,axis=1); P.columns=[f'{b}_{a}' for a,b in P.columns]; P=P.reset_index()
P.to_csv('output/ohio/rac_tele_by_place_2015_2019_2023.csv',index=False)
S=pd.DataFrame({y:100*P.groupby('cls')[f'T_{y}'].sum()/P[f'T_{y}'].sum() for y in (2015,2019,2023)})
S.to_csv('output/ohio/residence_pattern.csv',index_label='cls'); print(S.round(2).to_string())
