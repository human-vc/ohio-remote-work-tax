import pandas as pd,numpy as np
S=pd.read_csv('output/revenue/sample_primary_with_controls.csv',dtype={'stplc':str})
cols=['Gain','Loss','rev2019','resident_workers','tax_rate','credit_factor','res_tele','res_high_earn','res_goods','res_trade_transport']
d=S[cols].copy(); d['rev2019']=d.rev2019/1e6
T=d.describe().T[['mean','std','50%']]
T.to_csv('output/revenue/summary_statistics.csv'); print(T.round(3).to_string())
print('cities',(S.cls=='city').sum(),'villages',(S.cls=='village').sum(),'counties',S.county.nunique(),'metros',S.metro.nunique())
X=pd.concat([pd.get_dummies(S.metro,dtype=float),S[['res_tele','res_high_earn','res_goods','res_trade_transport','lrw']]],axis=1).values
b,*_=np.linalg.lstsq(X,S.Gain.values,rcond=None); res=S.Gain.values-X@b
r=pd.DataFrame({'raw_sd':[S.Gain.std()],'resid_sd':[res.std(ddof=1)]})
r.to_csv('output/revenue/exposure_residual_sd.csv',index=False); print(r.round(4).to_string(index=False))
