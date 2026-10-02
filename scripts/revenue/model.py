import pandas as pd,numpy as np,re,os,sys
YEARS=list(range(int(os.environ.get('YEAR_START','2016')),int(os.environ.get('YEAR_END','2024'))+1)); K=[y for y in YEARS if y!=2019]
POST=[int(x) for x in os.environ.get('POST_YEARS','2022,2023,2024').split(',')]
S=pd.read_csv(os.environ.get('SAMPLE','output/revenue/sample_primary_with_controls.csv'),dtype={'stplc':str}).set_index('stplc')
def norm(x): return re.sub(r'\s+',' ',re.sub(r'\s*\([^)]*\)','',str(x)).lower().replace('.','').replace('saint ','st ')).strip()
pl=pd.read_csv('data/ohio/st39_places.txt',sep='|',dtype=str); pl['k']=pl.PLACENAME.str.replace(r' (city|village)$','',regex=True).map(norm); pl['stplc']='39'+pl.PLACEFP
rc=pd.read_csv(os.environ.get('COLLECTIONS','data/ohio/rita_member_collections_2016_2025.csv')); rc['stplc']=rc.member.map(norm).map(pl.drop_duplicates('k').set_index('k').stplc)
Y=rc[rc.year.isin(YEARS)].groupby(['stplc','year']).net_collections.sum()
if os.environ.get('AOS_OUTCOME'):
    ao=pd.read_csv(os.environ['AOS_OUTCOME'],dtype={'stplc':str}); Y=ao[ao.fy.isin(YEARS)].rename(columns={'fy':'year'}).groupby(['stplc','year']).gw_income_tax.sum()
    if os.environ.get('AOS_MINUS_RITA'):
        Yr=rc[rc.year.isin(YEARS)].groupby(['stplc','year']).net_collections.sum(); Y=(Y/Yr).dropna()
if os.environ.get('COMPONENT'):
    cc=pd.read_csv(os.environ.get('COMPONENT_FILE','data/ohio/components_clean.csv')); cc['stplc']=cc.city.map(norm).map(pl.drop_duplicates('k').set_index('k').stplc)
    cc['year']=cc.year.astype(int); Y=cc[cc.year.isin(YEARS)].groupby(['stplc','year'])[os.environ['COMPONENT']].sum()
    S=S[S.index.isin(cc.stplc.dropna())]; print('COMPONENT',os.environ['COMPONENT'],'cities',len(S))
d=pd.DataFrame([(i,t) for i in S.index for t in YEARS],columns=['stplc','year'])
_v=d.set_index(['stplc','year']).index.map(lambda k: Y.get(k,np.nan)); d['y']=np.asarray(_v,float) if os.environ.get('NOLOG') else np.log(_v)
if os.environ.get('SOI_RATIO'):
    sw=pd.read_csv(os.environ.get('SOI_FILE','output/revenue/soi_place_wages_2016_2022.csv'),dtype={'stplc':str}).set_index('stplc'); sw.columns=[c.replace('.0','') for c in sw.columns]
    keep=sw.index[(sw[[str(y) for y in YEARS]].notna().all(1))&(sw.purity>=float(os.environ.get('PURITY','0')))]
    d=d[d.stplc.isin(keep)].copy()
    lw=np.log(d.apply(lambda r: sw.loc[r.stplc,str(r.year)],axis=1))
    mode=os.environ.get('SOI_MODE','ratio')
    d['y']= d.y-lw if mode=='ratio' else (lw if mode=='wage' else d.y)
    print('SOI_MODE',mode)
    if os.environ.get('KEEP_FILE'):
        kf=pd.read_csv(os.environ['KEEP_FILE'],dtype={'stplc':str}).set_index('stplc').iloc[:,0]
        d=d[d.stplc.map(kf)==int(os.environ['KEEP_VAL'])].copy(); print('KEEP',os.environ['KEEP_FILE'],os.environ['KEEP_VAL'],'places',d.stplc.nunique())
    print('SOI_RATIO sample places',d.stplc.nunique(),'purity>=',os.environ.get('PURITY','0'))
d=d.join(S[[c for c in ['Potential'] if c in S]+['metro','county','Gain','Loss','res_tele','res_high_earn','res_goods','res_trade_transport','lrw']],on='stplc')
bad=d[~np.isfinite(d.y)].stplc.unique()
print('places with missing/nonpositive collections in 2016-2024 (dropped from estimation):',len(bad),list(bad)[:10])
d=d[~d.stplc.isin(bad)].reset_index(drop=True)
_ex=os.environ.get('EXCLUDE_COL'),os.environ.get('EXCLUDE_VAL')
if _ex[0]: d=d[~d[_ex[0]].astype(str).isin(_ex[1].split(','))].reset_index(drop=True); print('EXCLUDED',_ex)
X=['res_tele','res_high_earn','res_goods','res_trade_transport','lrw']
R=pd.DataFrame({f'Gain_{k}':d.Gain*(d.year==k) for k in K}|{f'Loss_{k}':d.Loss*(d.year==k) for k in K})
N=[pd.get_dummies(d.stplc,prefix='p').astype(float),pd.get_dummies(d.metro+'_'+d.year.astype(str),prefix='my').astype(float)]
if not os.environ.get('NO_CONTROLS'): N.append(pd.DataFrame({f'{x}_{k}':d[x]*(d.year==k) for x in X for k in K}))
if os.environ.get('ADD_POTENTIAL'): N.append(pd.DataFrame({f'Pot_{k}':d.Potential*(d.year==k) for k in K})); print('ADDED Potential x year to nuisance block')
N=pd.concat(N,axis=1).values
def res(A):
    b,*_=np.linalg.lstsq(N,A,rcond=None); return A-N@b
yr=res(d.y.values); Rr=res(R.values)
keep=Rr.std(0)>1e-10; names=np.array(R.columns)[keep]; Rr=Rr[:,keep]
beta,*_=np.linalg.lstsq(Rr,yr,rcond=None); e=yr-Rr@beta
within_r2=1-(e@e)/(yr@yr)

from scipy import stats
n=len(yr); kN=np.linalg.matrix_rank(N); kR=Rr.shape[1]
kTot=kN-d.stplc.nunique()+kR
Mproj=np.eye(n)-N@np.linalg.pinv(N)
XtXi=np.linalg.pinv(Rr.T@Rr)
def V_cr(ee,cl,small=True):
    ug=np.unique(cl); M=np.zeros((kR,kR))
    for g in ug:
        ix=cl==g; s=Rr[ix].T@ee[ix]; M+=np.outer(s,s)
    V=XtXi@M@XtXi
    if small: V*=len(ug)/(len(ug)-1)*(n-1)/(n-kTot)
    return V
def wald_boot(W,cl,B,seed):
    rng=np.random.default_rng(seed)
    A=XtXi@W.T@np.linalg.pinv(W@XtXi@W.T)
    b0=beta-A@(W@beta); u0=yr-Rr@b0
    ug=np.unique(cl); gi=np.searchsorted(ug,cl)
    def stat(yy):
        yy=Mproj@yy; bb=XtXi@(Rr.T@yy); ee=yy-Rr@bb
        V=V_cr(ee,cl); d=W@bb
        return float(d@np.linalg.pinv(W@V@W.T)@d)
    s0=stat(yr); cnt=0
    for _ in range(B):
        v=rng.choice([-1.0,1.0],size=len(ug))[gi]
        if stat(Rr@b0+u0*v)>=s0-1e-12: cnt+=1
    return s0,(cnt+1)/(B+1)
cl_c=d.county.values; cl_m=d.metro.values
Vc=V_cr(e,cl_c); Vm=V_cr(e,cl_m)
Gc=len(np.unique(cl_c)); Gm=len(np.unique(cl_m))
tc=stats.t.ppf(.975,Gc-1)
out=pd.DataFrame({'coef':beta,'se_county':np.sqrt(np.diag(Vc)),'se_metro':np.sqrt(np.diag(Vm))},index=names)
out['ci95_county_lo']=out.coef-tc*out.se_county; out['ci95_county_hi']=out.coef+tc*out.se_county
print(f'N obs {n}, places {d.stplc.nunique()}, county clusters {Gc}, metro clusters {Gm}, nuisance rank {kN}, within R2 {within_r2:.4f}')
print(out.round(4).to_string())
if os.environ.get('SAVE_VCV'):
    gi=[i for i,x in enumerate(names) if x.startswith('Gain_')]
    tag=os.environ.get('OUT_TAG','main')
    pd.Series(beta[gi],index=names[gi]).to_csv(f'output/revenue/model_{tag}_beta.csv',header=['coef'])
    pd.DataFrame(Vc[np.ix_(gi,gi)],index=names[gi],columns=names[gi]).to_csv(f'output/revenue/model_{tag}_vcv.csv')
B=int(sys.argv[1]) if len(sys.argv)>1 else 1999
if B==0:
    w=np.mean([np.array([1.0 if x==f'Gain_{y}' else 0.0 for x in names]) for y in (2022,2023,2024)],axis=0)
    print('LOO_GAIN_POST',(w@beta).item(),np.sqrt(w@Vc@w).item(),d.stplc.nunique()); sys.exit()
def row(nm): return np.array([1.0 if x==nm else 0.0 for x in names])
res=[]
for pre in ['Gain','Loss']:
    w=np.mean([row(f'{pre}_{y}') for y in POST],axis=0)[None,:]
    th=(w@beta).item(); se=np.sqrt(w@Vc@w.T).item(); s,p=wald_boot(w,cl_c,B,1)
    res.append((pre,'post mean '+'-'.join(map(str,POST)),th,se,th-tc*se,th+tc*se,p))
    Wj=np.vstack([row(f'{pre}_{y}') for y in (2016,2017,2018) if y in YEARS])
    dj=Wj@beta; Fj=float(dj@np.linalg.pinv(Wj@Vc@Wj.T)@dj)/len(dj)
    pF=1-stats.f.cdf(Fj,len(dj),Gc-1); s2,pb=wald_boot(Wj,cl_c,B,2)
    res.append((pre,'joint pre 2016-18 = 0 (F)',Fj,np.nan,np.nan,np.nan,pb))
    print(f'{pre} joint pre-test: F={Fj:.2f} analytic p={pF:.3f} wild-boot p={pb:.3f}')
    PRE=[y for y in YEARS if y<2019]
    if len(PRE)>3:
        Wa=np.vstack([row(f'{pre}_{y}') for y in PRE]); da=Wa@beta; Fa=float(da@np.linalg.pinv(Wa@Vc@Wa.T)@da)/len(PRE)
        s3,pa=wald_boot(Wa,cl_c,B,4)
        res.append((pre,f'joint pre {PRE[0]}-18 = 0 (F)',Fa,np.nan,np.nan,np.nan,pa))
        print(f'{pre} full pre-test {PRE[0]}-18: F={Fa:.2f} analytic p={1-stats.f.cdf(Fa,len(PRE),Gc-1):.3f} wild-boot p={pa:.3f}')
if os.environ.get('CONTRAST'):
    a,b_=os.environ['CONTRAST'].split('-')
    wc=(row(f'Gain_{a}')-row(f'Gain_{b_}'))[None,:]; th=(wc@beta).item(); se=np.sqrt(wc@Vc@wc.T).item()
    sB,pB=wald_boot(wc,cl_c,B,3)
    print(f'CONTRAST Gain_{a} - Gain_{b_}: {th:.4f}, CR1 SE {se:.4f}, CI [{th-tc*se:.4f}, {th+tc*se:.4f}], wild p {pB:.3f}')
res.append(('all','within R2',within_r2,np.nan,np.nan,np.nan,np.nan))
R_=pd.DataFrame(res,columns=['exposure','estimand','estimate','se_county','ci_lo','ci_hi','wild_p_county'])
print(R_.round(4).to_string(index=False))
tag=os.environ.get('OUT_TAG','main'); out.to_csv(f'output/revenue/model_{tag}_results.csv'); R_.to_csv(f'output/revenue/model_{tag}_summary.csv',index=False)
