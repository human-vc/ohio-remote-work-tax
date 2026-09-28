import pandas as pd,re
def norm(x): return re.sub(r'\s+',' ',re.sub(r'\s*\([^)]*\)','',str(x)).lower().replace('.','').replace('saint ','st ')).strip()
pl=pd.read_csv('data/ohio/st39_places.txt',sep='|',dtype=str); pl['k']=pl.PLACENAME.str.replace(r' (city|village)$','',regex=True).map(norm); pl['stplc']='39'+pl.PLACEFP
rc=pd.read_csv('data/ohio/rita_member_collections_2016_2025.csv'); rc['stplc']=rc.member.map(norm).map(pl.drop_duplicates('k').set_index('k').stplc)
avg=rc[rc.year.isin([2016,2017,2018])].groupby('stplc').net_collections.sum()/3
for src,dst in [('output/revenue/sample_primary_with_controls.csv','output/revenue/sample_altnorm_121.csv'),('output/revenue/sample_preperiod_2012.csv','output/revenue/sample_altnorm_85.csv')]:
    S=pd.read_csv(src,dtype={'stplc':str}); a=S.stplc.map(avg)
    assert a.notna().all() and (a>0).all()
    f=S.rev2019/a
    for c in ['Gain','Loss']: S[c+'_2019norm']=S[c]; S[c]=S[c]*f
    S.to_csv(dst,index=False)
    print(dst,len(S),'Gain sd %.3f -> %.3f corr %.3f'%(S.Gain_2019norm.std(),S.Gain.std(),S.Gain.corr(S.Gain_2019norm)))
