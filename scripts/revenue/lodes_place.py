import pandas as pd
xw=pd.read_csv('data/raw/lodes/oh_xwalk.csv.gz',usecols=['tabblk2020','stplc','stplcname','ctycsubname'],dtype=str)
m=dict(zip(xw.tabblk2020,xw.stplc)); names=dict(zip(xw.stplc,xw.stplcname))
out=[]
for y in (2019,2023):
    agg={}
    for ch in pd.read_csv(f'data/raw/lodes/oh_od_main_JT00_{y}.csv.gz',usecols=['w_geocode','h_geocode','S000'],dtype={'w_geocode':str,'h_geocode':str},chunksize=1_000_000):
        ch['wp']=ch.w_geocode.map(m).fillna('9999999'); ch['hp']=ch.h_geocode.map(m).fillna('9999999')
        g=ch.groupby(['wp','hp']).S000.sum()
        for k,v in g.items(): agg[k]=agg.get(k,0)+v
    s=pd.Series(agg); s.index=pd.MultiIndex.from_tuples(s.index,names=['wp','hp'])
    df=s.reset_index(name='jobs'); df['year']=y; out.append(df)
df=pd.concat(out); df['work_place']=df.wp.map(names); df['home_place']=df.hp.map(names)
df.to_csv('output/revenue/lodes_place_od_2019_2023.csv.gz',index=False)
rows=[]
for y in (2019,2023):
    d=df[df.year==y]
    work=d.groupby('wp').jobs.sum(); home=d.groupby('hp').jobs.sum(); same=d[d.wp==d.hp].set_index('wp').jobs
    t=pd.DataFrame({'jobs_located':work,'resident_workers':home,'live_work_same':same}).fillna(0)
    t['in_commuter_share']=1-t.live_work_same/t.jobs_located; t['out_commuter_share']=1-t.live_work_same/t.resident_workers
    t['jobs_per_resident_worker']=t.jobs_located/t.resident_workers; t['year']=y; t['place']=t.index.map(names); rows.append(t)
T=pd.concat(rows).reset_index(names='stplc'); T=T[T.stplc!='9999999']
T.to_csv('output/revenue/lodes_place_exposure.csv',index=False)
S=['Columbus city','Cleveland city','Cincinnati city','Dayton city','Akron city','Toledo city','Dublin city','Westerville city','Hilliard city','Mason city','Solon city','Upper Arlington city','Worthington city','Bexley city']
print(T[(T.place.isin(S))&(T.year==2023)][['place','jobs_located','resident_workers','in_commuter_share','out_commuter_share','jobs_per_resident_worker']].round(3).to_string(index=False))
print('places',T.place.nunique())
