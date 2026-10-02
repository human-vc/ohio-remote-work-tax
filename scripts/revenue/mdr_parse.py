import re,sys,subprocess,pandas as pd
num=r'(-?[\d,]+\.\d\d)'
cols=['total','wh_tax','wh_pi','wh_ref','ind_tax','ind_pi','ind_ref','np_tax','np_pi','np_ref']
rows=[]
for rep in range(2019,2025):
    txt=subprocess.run(['pdftotext','-layout',f'{sys.argv[1]}/MDR for All - {rep}.pdf','-'],capture_output=True,text=True,errors='ignore').stdout
    cur=None;cash=False
    for line in txt.splitlines():
        m=re.search(r'(CASH )?PERIOD \d+ DISTRIBUTION FOR (.+?)\s*$',line)
        if m: cur=m.group(2).strip(); cash=bool(m.group(1)); continue
        m=re.match(r'^YTD (20\d\d)\s+'+r'\s+'.join([num]*10)+r'\s*$',line)
        if m and cur and cash:
            rows.append({'report':rep,'muni':cur,'year':int(m.group(1)),**dict(zip(cols,[float(x.replace(',','')) for x in m.groups()[1:]]))})
d=pd.DataFrame(rows)
for g in ['wh','ind','np']: d[g]=d[g+'_tax']+d[g+'_pi']+d[g+'_ref']
d.to_csv('data/ohio/rita_mdr_cash_ytd.csv',index=False)
