import pandas as pd, glob, re, warnings; warnings.filterwarnings('ignore')
rows=[]
for f in sorted(glob.glob('data/raw/odt_y2/*')):
    x=pd.read_excel(f,header=None)
    ty=int(re.search(r'TAX YEAR (\d{4})',str(x.iloc[0,0])).group(1))
    hdr=[' '.join(str(v) for v in x.iloc[3:10,c] if str(v)!='nan').upper() for c in x.columns]
    def col(*keys,excl=()):
        c=[i for i,h in enumerate(hdr) if all(k in h for k in keys) and not any(e in h for e in excl)]
        return c[0]
    m={'county':0,'district_name':1,'pun':col('PUN') if any('PUN' in h for h in hdr) else 2,'irn':col('IRN'),
       'returns':col('NUMBER OF RETURNS'),'exemptions':col('EXEMPTIONS'),
       'fagi_total':col('TOTAL FEDERAL'),'fagi_median':col('MEDIAN FEDERAL',excl=('RANK',)),
       'oagi_total':col('TOTAL OHIO ADJUSTED'),'oagi_median':col('MEDIAN OHIO',excl=('RANK',)),
       'oh_tax_liability':col('INCOME TAX LIABILITY') if any('INCOME TAX LIABILITY' in h for h in hdr) else col('LIABILITY')}
    d=x.iloc[10:,list(m.values())]; d.columns=list(m)
    d=d[pd.to_numeric(d.irn,errors='coerce').notna()].copy()
    d['irn']=d.irn.astype(int); d['tax_year']=ty
    for c in ['returns','exemptions','fagi_total','fagi_median','oagi_total','oagi_median','oh_tax_liability']: d[c]=pd.to_numeric(d[c],errors='coerce')
    rows.append(d); print(ty,len(d),int(d.returns.sum()),round(d.fagi_total.sum()/1e9,1))
p=pd.concat(rows); p['county']=p.county.str.strip(); p['district_name']=p.district_name.str.strip()
p.sort_values(['irn','tax_year']).to_csv('output/revenue/sd_income_panel_2012_2024.csv',index=False)
print(p.groupby('tax_year').irn.nunique().to_dict()); print('balanced irns', (p.groupby('irn').tax_year.nunique()==13).sum())
