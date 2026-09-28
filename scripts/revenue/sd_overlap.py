import pandas as pd, json
bs=pd.read_csv('data/raw/baf/BlockAssign_ST39_OH_SDUNI.txt',sep='|',dtype=str)
bp=pd.read_csv('data/raw/baf/BlockAssign_ST39_OH_INCPLACE_CDP.txt',sep='|',dtype=str)
b=bs.merge(bp,on='BLOCKID',how='outer')
rac=pd.read_csv('data/raw/lodes/oh_rac_S000_JT00_2019.csv.gz',usecols=['h_geocode','C000'],dtype={'h_geocode':str})
b=b.merge(rac.rename(columns={'h_geocode':'BLOCKID'}),on='BLOCKID',how='left').fillna({'C000':0})
xw=pd.read_csv('data/raw/lodes/oh_xwalk.csv.gz',usecols=['tabblk2020','stschool'],dtype=str)
chk=b.merge(xw,left_on='BLOCKID',right_on='tabblk2020',how='left')
print('blocks',len(b),'rac matched workers',b.C000.sum(),'of',rac.C000.sum())
print('xwalk stschool == 39+BAF SDUNI share:',(chk.stschool==('39'+chk.DISTRICT.fillna(''))).mean())
b['stplc']=('39'+b.PLACEFP).where(b.PLACEFP.notna())
b['leaid']='39'+b.DISTRICT
ccd=pd.DataFrame(json.load(open('data/raw/ccd/urban_ccd_lea_oh_2019.json'))['results'])
ccd['irn']=ccd.state_leaid.str.replace('OH-','').astype(int)
b=b.merge(ccd[['leaid','irn','lea_name']],on='leaid',how='left')
print('blocks w/o IRN match, workers:',b.loc[b.irn.isna(),'C000'].sum())
pd_=b[b.stplc.notna()].groupby(['stplc','leaid','irn','lea_name'],as_index=False).C000.sum()
pd_['place_workers']=pd_.groupby('stplc').C000.transform('sum')
pd_['share_of_place']=pd_.C000/pd_.place_workers
dw=b.groupby('leaid').C000.sum().rename('district_workers')
pd_=pd_.join(dw,on='leaid'); pd_['share_of_district']=pd_.C000/pd_.district_workers
pd_.rename(columns={'C000':'workers_2019'}).to_csv('output/revenue/sd_place_district_xwalk.csv',index=False)
samp={'primary':pd.read_csv('output/revenue/sample_primary.csv',dtype={'stplc':str}),'aos':pd.read_csv('output/revenue/sample_aos.csv',dtype={'stplc':str})}
out=[]
for k,s in samp.items():
    m=pd_[pd_.stplc.isin(s.stplc)]
    top=m.sort_values('share_of_place').groupby('stplc').tail(1)
    miss=set(s.stplc)-set(m.stplc)
    r={'sample':k,'n':len(s),'unmatched':len(miss)}
    for t in [.5,.8,.9,.95]: r[f'modal_sd_share>={t}']=int((top.share_of_place>=t).sum())
    r['distinct_districts_any']=m.leaid.nunique()
    r['distinct_modal_districts']=top.leaid.nunique()
    both=top[(top.share_of_place>=.8)&(top.share_of_district>=.5)]
    r['place>=80%_in_one_SD_and_SD>=50%_place']=len(both)
    both=top[(top.share_of_place>=.8)&(top.share_of_district>=.8)]
    r['place>=80%_in_one_SD_and_SD>=80%_place']=len(both)
    r['median_place_share_of_modal_district']=round(top.share_of_district.median(),3)
    out.append(r); print(k,'unmatched',sorted(miss)[:10])
    top.merge(s[['stplc','name']],on='stplc').to_csv(f'output/revenue/sd_modal_district_{k}.csv',index=False)
print(pd.DataFrame(out).T.to_string())
pd.DataFrame(out).to_csv('output/revenue/sd_overlap_summary.csv',index=False)
