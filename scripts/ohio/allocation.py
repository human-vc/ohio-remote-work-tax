import pandas as pd,numpy as np,re,os,itertools
od=pd.read_csv('output/ohio/od_place_2019_bands.csv.gz',dtype={'hp':str,'wp':str})
Sc=pd.read_csv('output/ohio/schedule_2019_12_31.csv',dtype={'stplc':str}).set_index('stplc')
pl=pd.read_csv('data/ohio/st39_places.txt',sep='|',dtype=str); pl['stplc']='39'+pl.PLACEFP
pl['kind']=np.where(pl.PLACENAME.str.endswith(' CDP'),'cdp',np.where(pl.PLACENAME.str.endswith(' city'),'city',np.where(pl.PLACENAME.str.endswith(' village'),'village','other')))
pl['base']=pl.PLACENAME.str.replace(r' (city|village|CDP)$','',regex=True).str.upper().str.replace('.','',regex=False).str.replace('SAINT ','ST ',regex=False)
F=pd.read_csv('data/ohio/finder_muni_20200711195940.csv',header=None,names=['frm','to','code','name','rate'],dtype=str)
F=F[(F.frm.astype(int)<=20191231)&(F.to.astype(int)>=20191231)].copy()
F['rate']=F.rate.astype(float)*100
F['base']=F.name.str.replace(r' (CITY|VILLAGE)$','',regex=True).str.replace('.','',regex=False).str.replace('SAINT ','ST ',regex=False).str.strip()
inc=pl[pl.kind.isin(['city','village'])]
bycode=dict(zip(inc.PLACEFP,inc.stplc)); name_ct=inc.base.value_counts()
m={} ; amb=[]
for r in F.itertuples():
    full=r.name.replace('.','').replace('SAINT ','ST ').strip()
    b20=inc.set_index('PLACEFP').base.get(r.code)
    if r.code in bycode and b20 is not None and (b20==r.base or b20==full or full.startswith(b20)): m[r.code]=bycode[r.code]; continue
    if name_ct.get(r.base,0)==1: m[r.code]=inc[inc.base==r.base].stplc.iloc[0]
    else: amb.append((r.code,r.name))
MANUAL={'81214':'3981718','76582':'3976582'}
m.update(MANUAL); amb=[a for a in amb if a[0] not in MANUAL]
F['stplc']=F.code.map(m)
fin=F.dropna(subset=['stplc']).drop_duplicates('stplc').set_index('stplc')
print('Finder taxing munis 12/31/2019:',len(F),'| mapped to 2020 places:',len(fin),'| ambiguous/unmapped:',len(amb),amb[:10])
def classify(p):
    if p in ('','9999999'): return 'unincorporated'
    k=pl.set_index('stplc').kind.get(p)
    if k=='cdp': return 'unincorporated'
    if p in fin.index or p in Sc.index: return 'taxing'
    return 'no tax per ODT list'
places=set(od.hp)|set(od.wp)
C={p:classify(p) for p in places}
amb_codes={bycode.get(c) for c,_ in amb if c in bycode}
for p in places:
    if p in amb_codes and p not in Sc.index: C[p]='unresolved (ambiguous name)'
NO_TAX_20191231={'3937842','3979282','3981732','3912504','3921560','3936918','3940054','3949042','3952416'}
for p in NO_TAX_20191231:
    if p in C: C[p]='no tax per ODT list'
rate=Sc.tax_rate.combine_first(fin.rate)
fac=Sc.credit_factor; cap=Sc.credit_cap
def run(W,tele_mode='DN',unres='low'):
    d=od.copy(); d['earn']=sum(d[k]*v for k,v in W.items())*12
    tele=pd.read_csv('output/ohio/place_teleworkability_2019.csv'); tmap=dict(zip(tele.stplcname,tele.teleworkable_share_DN)); pn=dict(zip(pl.stplc,pl.PLACENAME+', OH'))
    d['tw']=d.wp.map(lambda p: tmap.get(pn.get(p,''),np.nan)); d['tw']=d.tw.fillna(d.tw.mean()) if tele_mode=='DN' else 1.0
    d['wcls']=d.wp.map(C); d['rcls']=d.hp.map(C)
    d=d[(d.hp!=d.wp)&(d.wcls=='taxing')].copy()
    d['t_w']=d.wp.map(rate)
    d['t_r']=np.where(d.rcls=='taxing',d.hp.map(rate),0.0)
    f=d.hp.map(fac)/100; c=d.hp.map(cap)
    unknown=(d.rcls=='taxing')&(f.isna()|c.isna()|d.t_r.isna())
    unk_res=d.rcls.str.startswith('unresolved')
    if unres=='low':
        f=f.fillna(0); c=c.fillna(0); d['t_r']=d.t_r.fillna(0)
    else:
        f=f.fillna(1.0); d['t_r']=d.t_r.fillna(d.t_w); c=c.fillna(d.t_r)
        d.loc[unk_res,'t_r']=d.loc[unk_res,'t_w']; f[unk_res]=1.0; c[unk_res]=d.loc[unk_res,'t_w']
    d['cr']=np.minimum(f*np.minimum(d.t_w,c),d.t_r)
    b=d.earn*d.tw/100; wl=(b*d.t_w).sum(); rg=(b*d.cr).sum()
    unk_share=(b*d.t_w)[unknown|unk_res].sum()/wl
    return rg/wl, unk_share, d
res=[]
for (lab,W),tm,u in itertools.product([('base 800/2300/6000',{'SE01':800,'SE02':2300,'SE03':6000}),('low 600/2000/4500',{'SE01':600,'SE02':2000,'SE03':4500}),('high 1000/2800/9000',{'SE01':1000,'SE02':2800,'SE03':9000})],['DN','uniform'],['low','high']):
    s,us,_=run(W,tm,u); res.append((lab,tm,u,round(s,3),round(1-s,3),round(us,3)))
R=pd.DataFrame(res,columns=['earnings bands','teleworkability','unknowns treated as','share to residence','share to workers','loss share with unknown residence terms'])
print(R.to_string(index=False))
s,us,d=run({'SE01':800,'SE02':2300,'SE03':6000},'DN','low')
b=d.earn*d.tw/100
tab=pd.DataFrame({'loss':(b*d.t_w).groupby(d.rcls).sum(),'res':(b*d.cr).groupby(d.rcls).sum()}); tab['share_of_loss']=tab.loss/tab.loss.sum(); tab['to_residence']=tab.res/tab.loss
print('\nbase case by residence classification:'); print(tab[['share_of_loss','to_residence']].round(3).to_string())
pd.Series(C).rename('class').to_csv('output/ohio/place_tax_classification_2019.csv',index_label='stplc')
R.to_csv('output/ohio/allocation_sensitivity.csv',index=False)
