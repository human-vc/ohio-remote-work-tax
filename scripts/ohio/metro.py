import runpy,io,contextlib
import pandas as pd,numpy as np
with contextlib.redirect_stdout(io.StringIO()):
    g=runpy.run_path('scripts/ohio/allocation.py')
_,_,d=g['run']({'SE01':800,'SE02':2300,'SE03':6000},'DN','low')
pl=g['pl']
cb=pd.read_csv('data/ohio/oh_county_cbsa.csv',dtype=str)
metro=dict(zip(cb.county,cb['CBSA Code'])); title=dict(zip(cb['CBSA Code'],cb['CBSA Title']))
county=dict(zip(pl.stplc,pl.COUNTIES.str.split('~~~').str[0]))
d['metro']=d.wp.map(county).map(metro).fillna('nonmetro')
b=d.earn*d.tw/100
tax=d.rcls=='taxing'
d['loss']=b*d.t_w
d['home']=b*d.cr
d['untaxed']=np.where(tax,0,b*d.t_w)
d['rate']=np.where(tax,b*np.maximum(d.t_w-d.t_r,0),0)
d['credit']=np.where(tax,b*(np.minimum(d.t_w,d.t_r)-d.cr),0)
cols=['loss','home','untaxed','rate','credit']
G=d.groupby('metro')[cols].sum().sort_values('loss',ascending=False)
top=G.head(6).copy(); top.index=[title.get(i,i) for i in top.index]
top.loc['All other areas']=G.iloc[6:].sum()
top.loc['Ohio']=G.sum()
out=pd.DataFrame({'share_of_losses':top.loss/G.loss.sum()*100})
for c in cols[1:]: out[c]=top[c]/top.loss*100
out['workers']=100-out.home
out.round(2).to_csv('output/ohio/allocation_by_metro.csv',index_label='workplace_area')
print(out.round(1).to_string())
