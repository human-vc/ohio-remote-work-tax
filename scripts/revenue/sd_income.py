import pandas as pd, numpy as np
xw=pd.read_csv('output/revenue/sd_place_district_xwalk.csv',dtype={'stplc':str})
y2=pd.read_csv('output/revenue/sd_income_panel_2012_2024.csv')
y2['lfagi']=np.log(y2.fagi_total); y2['lret']=np.log(y2.returns)
print('xwalk districts found in Y2:',xw.irn.isin(y2.irn).mean().round(4),'worker share',(xw.workers_2019*xw.irn.isin(y2.irn)).sum()/xw.workers_2019.sum())
m=xw.merge(y2[['irn','tax_year','lfagi','lret','fagi_total','returns']],on='irn')
base=m[m.tax_year==2019][['stplc','irn','lfagi','lret']].rename(columns={'lfagi':'b','lret':'br'})
m=m.merge(base,on=['stplc','irn']); m['dl']=m.lfagi-m.b; m['dr']=m.lret-m.br
pl=m.groupby(['stplc','tax_year']).apply(lambda g: pd.Series({'dlfagi':np.average(g.dl,weights=g.workers_2019),'dlreturns':np.average(g.dr,weights=g.workers_2019)}),include_groups=False).reset_index()
pl.to_csv('output/revenue/sd_income_growth_vs2019.csv',index=False)
w=pl[pl.tax_year.between(2016,2024)].pivot(index='stplc',columns='tax_year',values='dlfagi')
w=np.exp(w); w.columns=[f'{c}.0' for c in w.columns]; w['purity']=1.0
w.to_csv('output/revenue/sd_fagi_as_wages.csv')
