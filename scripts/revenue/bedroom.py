import pandas as pd,numpy as np
S=pd.read_csv('output/revenue/sample_primary_with_controls.csv',dtype={'stplc':str}).set_index('stplc')
E=pd.read_csv('output/revenue/lodes_place_exposure.csv',dtype={'stplc':str}).query('year==2019').set_index('stplc')
sw=pd.read_csv('output/revenue/soi_place_wages_2016_2022.csv',dtype={'stplc':str}).set_index('stplc')
S['jpr']=E.jobs_per_resident_worker.reindex(S.index); S['purity']=sw.purity.reindex(S.index)
sub=S[S.purity>=0.30]
med=sub.jpr.median(); print('purity>=0.30 n',len(sub),'median jobs per resident worker',round(med,3))
pd.Series((sub.jpr<med).astype(int),name='bedroom').to_csv('output/revenue/bedroom_purityge030.csv',index_label='stplc')
