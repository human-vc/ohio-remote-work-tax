import re, csv, collections, pandas as pd
L=open('data/ohio/rita_afr_2015.txt').read().split('\n')
YRS=list(range(2015,2005,-1))
norm=lambda s: re.sub(r'[^a-z]','',re.sub(r'^saint ','st ',s.strip().lower()))
def num(v):
    v=v.replace('$','').replace(',','').replace('%','').strip()
    if v in ('-',''): return 0.0
    if v.startswith('(') : return -float(v.strip('()'))
    return float(v)
rec={}; sec=False
for l in L:
    if 'Municipal Income Tax Receipts - Last Ten' in l: sec=True; continue
    if sec and ('Expenses by Type' in l or 'Operating Indicators' in l): sec=False
    if not sec: continue
    m=re.match(r'^(\S.*?)\s{2,}([A-Z]\s+)?(\$?\s*[\d,\(\)\-]+.*)$',l)
    if not m: continue
    vals=re.findall(r'\(?[\d,]+\)?|(?<=\s)-(?=\s|$)',' '+m[3].replace('$',' ')+' ')
    if len(vals)!=10: continue
    rec[norm(m[1])]=(m[1].strip(),dict(zip(YRS,map(num,vals))))
rate=collections.defaultdict(dict); sec=False; cur=None; pend=''
for l in L:
    if 'Municipal Income Tax Rates, Credit Factors and Rates - Last Ten' in l: sec=True; continue
    if sec and 'Population - Last Ten' in l: sec=False
    if not sec: continue
    m=re.match(r'^(.*?)\s*(Tax Rate|Credit Factor|Credit Rate)\s+(.*)$',l)
    if not m:
        if l.strip() and not re.search(r'\d{4}\s+\d{4}',l): pend=l.strip()
        continue
    nm=m[1].strip()
    if nm: cur=norm((pend+' '+nm) if (pend and l.startswith(' ')) else nm); pend=''
    elif pend: cur=norm(pend); pend=''
    vs=m[3].split()
    if len(vs)!=10: continue
    rate[cur][m[2]]=dict(zip(YRS,[v.replace("%","") for v in vs]))
START=2012
r16=pd.read_csv('data/ohio/rita_rates_v2_long.csv')
r16['k']=r16.member.map(norm)
S=pd.read_csv('output/revenue/sample_primary_with_controls.csv',dtype={'stplc':str})
S['k']=S.name.map(norm)
def f(v):
    try: return float(v)
    except: return None
keep=[];why=collections.Counter()
for _,r in S.iterrows():
    n=r.k
    if n not in rec: why['no pre-2016 receipts']+=1; continue
    if not all(rec[n][1][y]>0 for y in range(START-1,2016)): why['not a full member from 2012']+=1; continue
    rr=rate.get(n,{})
    if not all(k in rr and len({rr[k][y] for y in range(START,2016)})==1 for k in ('Tax Rate','Credit Factor','Credit Rate')): why['rate/credit change 2012-15']+=1; continue
    b=r16[(r16.k==n)&(r16.year==2016)].set_index('field')
    ok=True
    for fld in ('Tax Rate','Credit Factor','Credit Rate'):
        v15=f(rr[fld][2015]); v16=b.loc[fld,'value_start'] if fld in b.index else None
        if v15 is None or v16 is None or pd.isna(v16) or abs(v15-float(v16))>1e-9: ok=False
    if not ok: why['change at 2015-16 boundary']+=1; continue
    keep.append(r.stplc)
print('retained',len(keep),dict(why))
S[S.stplc.isin(keep)].drop(columns='k').to_csv('output/revenue/sample_preperiod_2012.csv',index=False)
rows=[]
for n,(nm,vals) in rec.items():
    for y,v in vals.items(): rows.append((nm,'',y,v))
old=pd.DataFrame(rows,columns=['member','flag','year','net_collections'])
new=pd.read_csv('data/ohio/rita_member_collections_2016_2025.csv')
pd.concat([old[old.year<2016],new]).to_csv('output/revenue/rita_member_collections_2006_2025.csv',index=False)
R=S[S.stplc.isin(keep)]
print('counties',S.county.nunique(),'->',R.county.nunique())
