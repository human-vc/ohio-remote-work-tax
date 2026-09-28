import pandas as pd,numpy as np,re,os
S=pd.read_csv('output/revenue/sample_with_potential.csv',dtype={'stplc':str}).set_index('stplc')
V=['Potential','res_tele','res_high_earn','res_goods','res_trade_transport','lrw']
S['partial']=(S.credit_factor<100).astype(int)
mx=S.groupby('metro').partial.agg(['sum','count']); ok=mx[(mx['sum']>0)&(mx['sum']<mx['count'])].index
T=S[S.metro.isin(ok)]
Sig=np.linalg.pinv(np.cov(S[V].values.T))
pairs=[]
for i,r in T[T.partial==1].iterrows():
    C=T[(T.partial==0)&(T.metro==r.metro)]
    dd=C[V].values-r[V].values.astype(float); dist=np.einsum('ij,jk,ik->i',dd,Sig,dd)
    j=C.index[int(np.argmin(dist))]; pairs.append((i,j,float(np.sqrt(dist.min()))))
P=pd.DataFrame(pairs,columns=['partial','full','mdist'])
def std_diff(a,b): return (a.mean()-b.mean())/S[V].std()
before=std_diff(T[T.partial==1][V],T[T.partial==0][V]); after=std_diff(S.loc[P.partial,V],S.loc[P.full,V])
print('BALANCE (standardized mean differences, partial minus full):'); print(pd.DataFrame({'before (same metros)':before,'after matching':after}).round(3).to_string())
print(f'\npairs {len(P)}, distinct full-credit matches {P.full.nunique()}, metros {T.metro.nunique()}, counties {S.loc[P.partial,"county"].nunique()}')
def norm(x): return re.sub(r'\s+',' ',re.sub(r'\s*\([^)]*\)','',str(x)).lower().replace('.','').replace('saint ','st ')).strip()
pl=pd.read_csv('data/ohio/st39_places.txt',sep='|',dtype=str); pl['k']=pl.PLACENAME.str.replace(r' (city|village)$','',regex=True).map(norm); pl['stplc']='39'+pl.PLACEFP
rc=pd.read_csv('data/ohio/rita_member_collections_2016_2025.csv'); rc['stplc']=rc.member.map(norm).map(pl.drop_duplicates('k').set_index('k').stplc)
Y=np.log(rc[rc.year.between(2016,2024)].pivot_table(index='stplc',columns='year',values='net_collections',aggfunc='sum'))
post=Y[[2022,2023,2024]].mean(1)-Y[[2016,2017,2018,2019]].mean(1)
plac=Y[[2018,2019]].mean(1)-Y[[2016,2017]].mean(1)
P['name_partial']=S.loc[P.partial,'name'].values; P['name_full']=S.loc[P.full,'name'].values
P['metro']=S.loc[P.partial,'metro'].values; P['credit_partial']=S.loc[P.partial,'credit_factor'].values
P['gain_gap']=S.loc[P.partial,'Gain'].values-S.loc[P.full,'Gain'].values
P['pot_gap']=S.loc[P.partial,'Potential'].values-S.loc[P.full,'Potential'].values
P['dy_post']=post.reindex(P.partial).values-post.reindex(P.full).values
P['dy_placebo']=plac.reindex(P.partial).values-plac.reindex(P.full).values
print('\nPAIRS:'); print(P[['name_partial','credit_partial','name_full','metro','mdist','gain_gap','pot_gap','dy_post','dy_placebo']].round(3).to_string(index=False))
rng=np.random.default_rng(11)
cl=P.full.astype(str).values; ug=np.unique(cl); groups=[np.where(cl==g)[0] for g in ug]
def boot(col,B=4000):
    x,y=P.gain_gap.values,P[col].values; sl=np.polyfit(x,y,1)[0]; mn=y.mean(); bs=[];bm=[]
    for _ in range(B):
        ix=np.concatenate([groups[i] for i in rng.integers(0,len(groups),len(groups))])
        if np.ptp(x[ix])>0: bs.append(np.polyfit(x[ix],y[ix],1)[0]); bm.append(y[ix].mean())
    return sl,np.percentile(bs,[2.5,97.5]),mn,np.percentile(bm,[2.5,97.5])
print(f'pairs {len(P)}, bootstrap clusters (distinct full-credit matches) {len(ug)}')
out=[]
for col,lab in (('dy_post','POST 2022-24 vs 2016-19'),('dy_placebo','PLACEBO 2018-19 vs 2016-17')):
    sl,ci,mn,cim=boot(col); print(f'{lab}: slope {sl:.2f} [{ci[0]:.2f}, {ci[1]:.2f}] | mean diff {mn:.3f} [{cim[0]:.3f}, {cim[1]:.3f}]')
    out.append((col,sl,ci[0],ci[1],mn,cim[0],cim[1]))
pd.DataFrame(out,columns=['outcome','slope','slope_lo','slope_hi','mean_diff','mean_lo','mean_hi']).to_csv('output/revenue/matched_pairs_summary.csv',index=False)
P.to_csv('output/revenue/matched_pairs.csv',index=False)
