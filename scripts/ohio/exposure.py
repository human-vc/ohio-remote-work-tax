import pandas as pd, numpy as np, csv, re, os
xw=pd.read_csv('data/raw/lodes/oh_xwalk.csv.gz',usecols=['tabblk2020','stplc'],dtype={'tabblk2020':str,'stplc':str})
b2p=dict(zip(xw.tabblk2020,xw.stplc.fillna('')))
agg={}
for ch in pd.read_csv('data/raw/lodes/oh_od_main_JT00_2019.csv.gz',usecols=['w_geocode','h_geocode','S000','SE01','SE02','SE03'],dtype={'w_geocode':str,'h_geocode':str},chunksize=500_000):
    ch['wp']=ch.w_geocode.map(b2p).fillna(''); ch['hp']=ch.h_geocode.map(b2p).fillna('')
    g=ch.groupby(['hp','wp'])[['S000','SE01','SE02','SE03']].sum()
    for k,v in g.iterrows():
        a=agg.setdefault(k,np.zeros(4)); a+=v.values
od=pd.DataFrame([(h,w,*v) for (h,w),v in agg.items()],columns=['hp','wp','S000','SE01','SE02','SE03'])
od.to_csv('output/ohio/od_place_2019_bands.csv.gz',index=False)
print('od pairs',len(od),'jobs',od.S000.sum())
pl=pd.read_csv('data/ohio/st39_places.txt',sep='|',dtype=str)
pl['nm']=pl.PLACENAME.str.replace(r' (city|village)$','',regex=True).str.lower()
pl['stplc']='39'+pl.PLACEFP
def norm(x): return re.sub(r'\s+',' ',re.sub(r'\s*\([^)]*\)','',str(x)).lower().replace('.','').replace('saint ','st ')).strip()
pl['k']=pl.nm.map(norm)
rb=pd.read_csv('data/ohio/baseline_schedule_2019_12_31.csv')
rb=rb[(rb.member_on_2019_12_31==1)&rb.cls.isin(['city','village'])].copy()
rb['k']=rb.member.map(norm)
rb=rb.merge(pl[['k','stplc']].drop_duplicates('k'),on='k',how='left')
rb['admin']='RITA'
nr=pd.read_csv('data/ohio/nonrita_schedule_2019.csv',dtype={'fips':str})
nr=nr[nr.administrator!='RITA'].copy() if 'administrator' in nr else nr
nr['stplc']='39'+nr.fips.str.zfill(5)
sched=pd.concat([rb[['stplc','member','cls','admin','tax_rate','credit_factor','credit_cap']].rename(columns={'member':'name'}),
                 nr[['stplc','municipality','class','administrator','tax_rate','credit_factor','credit_cap']].rename(columns={'municipality':'name','class':'cls','administrator':'admin'})])
sched=sched.dropna(subset=['stplc']).drop_duplicates('stplc',keep='first')
for c in ['tax_rate','credit_factor','credit_cap']: sched[c]=pd.to_numeric(sched[c],errors='coerce')
print('schedule places',len(sched),'| RITA unmatched to fips:',rb.stplc.isna().sum(), list(rb[rb.stplc.isna()].member)[:10])
sched.to_csv('output/ohio/schedule_2019_12_31.csv',index=False)
S=sched.set_index('stplc')
tele=pd.read_csv('output/ohio/place_teleworkability_2019.csv')
tele['k']=tele.stplcname.str.replace(', OH','').str.replace(r' (city|village|CDP)$','',regex=True).map(norm)
pl2=pl.assign(k2=pl.PLACENAME.map(lambda s: norm(re.sub(r' (city|village)$','',s))))
tmap=dict(zip(tele.stplcname,tele.teleworkable_share_DN))
plname=dict(zip(pl.stplc,pl.PLACENAME+', OH'))
od['tele_w']=od.wp.map(lambda p: tmap.get(plname.get(p,''),np.nan))
W={'SE01':800,'SE02':2300,'SE03':6000}
od['earn']=sum(od[k]*v for k,v in W.items())*12
for c,src in (('t_w','tax_rate'),):
    od[c]=od.wp.map(S[src])
od['t_w']=od.t_w.fillna(0)
od['c_r']=od.hp.map(S.credit_factor)/100; od['cap_r']=od.hp.map(S.credit_cap); od['t_r']=od.hp.map(S.tax_rate)
x=od[(od.hp!='')&(od.hp!=od.wp)].copy()
x['cred_rate']=np.minimum(x.c_r*np.minimum(x.t_w,x.cap_r),x.t_r)
x['cred_rate_nodest']=np.minimum(x.c_r*x.cap_r,x.t_r)
x['below_cap']=(x.t_w<x.cap_r)&(x.c_r>0)
x['tw']=x.tele_w.fillna(x.tele_w.mean())
R=x.assign(g_jobs=x.S000*x.tw*x.cred_rate, g_earn=x.earn*x.tw*x.cred_rate/100, g_earn_nodest=x.earn*x.tw*x.cred_rate_nodest/100,
           out_earn_taxed=x.earn*(x.t_w>0), out_earn_below=x.earn*x.below_cap).groupby('hp')[['S000','g_jobs','g_earn','g_earn_nodest','out_earn_taxed','out_earn_below','earn']].sum()
resw=od[od.hp!=''].groupby('hp').S000.sum()
R['resident_workers']=resw
R=R.join(S,how='inner')
R['g_per_worker']=R.g_earn/R.resident_workers
R['share_out_earn_below_cap']=R.out_earn_below/R.out_earn_taxed
L=x[x.wp!=''].assign(l_earn=x.earn*x.tw*x.t_w/100).groupby('wp').l_earn.sum().rename('workplace_loss_index')
R=R.join(L,how='left')
rc=pd.read_csv('data/ohio/rita_member_collections_2016_2025.csv'); rc['k']=rc.member.map(norm)
rc=rc.merge(pl[['k','stplc']].drop_duplicates('k'),on='k')
rev19=rc[rc.year==2019].groupby('stplc').net_collections.sum()
aos=pd.read_csv('data/ohio/aos_city_income_tax_panel.csv'); aos['k']=aos.entity.str.replace(r'^(City|Village) of ','',regex=True).map(norm)
aos=aos.merge(pl[['k','stplc']].drop_duplicates('k'),on='k')
a19=aos[(aos.fy==2019)&(aos.basis=='GAAP')].groupby('stplc').gw_income_tax.sum()
R['rev2019']=rev19.reindex(R.index).fillna(a19.reindex(R.index))
R['gain_scenario_share_rev']=R.g_earn/R.rev2019
R.to_csv('output/ohio/exposure_2019.csv')
print('residence places with exposure',len(R),'| with rev2019',R.rev2019.notna().sum())
