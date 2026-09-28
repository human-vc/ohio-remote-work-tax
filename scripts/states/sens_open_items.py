import subprocess, json, shutil, itertools, pandas as pd, os
D='data/kentucky/'
PY='.venv/bin/python'
shutil.copy(D+'city_rates_2019_final.csv',D+'city_rates_2019_final.csv.sensbak'); shutil.copy(D+'county_rates_2019_final.csv',D+'county_rates_2019_final.csv.sensbak')
C0=pd.read_csv(D+'city_rates_2019_final.csv.sensbak',dtype=str); K0=pd.read_csv(D+'county_rates_2019_final.csv.sensbak',dtype=str)
def variant(somerset=None, shelby_credit=False, ms_merged=False):
    C=C0.copy(); K=K0.copy()
    if somerset is not None: C.loc[C.city=='Somerset','rate_2019_pct']=str(somerset)
    if shelby_credit: K.loc[K.county=='Shelby','credits_city_tax']='yes'
    if ms_merged:
        row={c:'' for c in C.columns}; row.update(city='Mount Sterling',county='Montgomery',rate_2019_pct='0.0')
        if 'evidence_class' in C: row['evidence_class']='sensitivity'
        C=pd.concat([C,pd.DataFrame([row])],ignore_index=True)
    C.to_csv(D+'city_rates_2019_final.csv',index=False); K.to_csv(D+'county_rates_2019_final.csv',index=False)
V={'base':{}, 'somerset_0':{'somerset':0.0}, 'somerset_1.2':{'somerset':1.2}, 'shelby_credit':{'shelby_credit':True}, 'mtsterling_merged':{'ms_merged':True},
   'all_low':{'somerset':0.0,'shelby_credit':True,'ms_merged':True}, 'all_high':{'somerset':1.2}}
out=open('output/states/sens_open_items.jsonl','w')
try:
    for name,kw in V.items():
        variant(**kw)
        for o,u,b,a in itertools.product(['stacked','credited'],['low','mid','high'],['low','base','high'],['zero','rate']):
            r=subprocess.run([PY,'scripts/states/ky_statewide.py','--keep-verified-no','--overlap',o,'--unres',u,'--bands',b,'--adopters',a],capture_output=True,text=True).stdout.strip().split('\n')[-1]
            d=json.loads(r); d['variant']=name; out.write(json.dumps(d)+'\n'); out.flush()
finally:
    shutil.copy(D+'city_rates_2019_final.csv.sensbak',D+'city_rates_2019_final.csv'); shutil.copy(D+'county_rates_2019_final.csv.sensbak',D+'county_rates_2019_final.csv')
    os.remove(D+'city_rates_2019_final.csv.sensbak'); os.remove(D+'county_rates_2019_final.csv.sensbak')
print('done')
