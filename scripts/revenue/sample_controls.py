import pandas as pd,numpy as np,os
S=pd.read_csv('output/revenue/sample_primary.csv',dtype={'stplc':str}).set_index('stplc')
C=pd.read_csv('output/ohio/controls_2019.csv',dtype={'stplc':str}).set_index('stplc')
cb=pd.read_csv('data/ohio/oh_county_cbsa.csv',dtype=str); m=dict(zip(cb.county,cb['CBSA Code']))
S['metro']=S.county.map(m).fillna('nonCBSA_'+S.county)
S=S.join(C)
S['Gain']=S.g_earn/S.rev2019; S['Loss']=S.workplace_loss_index.fillna(0)/S.rev2019
S['lrw']=np.log(S.resident_workers)
X=['res_tele','res_high_earn','res_goods','res_trade_transport','lrw']
def resid(y,df):
    D=pd.get_dummies(df.metro,drop_first=False).astype(float)
    Z=np.column_stack([df[X].values,D.values])
    b,*_=np.linalg.lstsq(Z,df[y].values,rcond=None); r=df[y].values-Z@b
    return r, 1-r.var()/df[y].var()
multi=S.groupby('metro').metro.transform('size')>=2
T=S[multi]
print('places total',len(S),'| in metros with >=2 places',len(T),'| metros',T.metro.nunique())
for y in ['Gain','Loss']:
    r,R2=resid(y,T)
    print(f'{y}: raw sd {T[y].std():.4f} | residual sd after controls+metro FE {r.std():.4f} | share of variance left {1-R2:.3f} | resid p10/p90 {np.percentile(r,10):.4f}/{np.percentile(r,90):.4f}')
rg,_=resid('Gain',T); rl,_=resid('Loss',T)
print('corr(resid Gain, resid Loss):',round(np.corrcoef(rg,rl)[0,1],3))
print('Gain raw distribution:',T.Gain.describe(percentiles=[.1,.5,.9]).round(4).to_dict())
S.to_csv('output/revenue/sample_primary_with_controls.csv',index_label='stplc')
