import pandas as pd
S=pd.read_csv('output/revenue/sample_primary_with_controls.csv',dtype={'stplc':str})
d=(S.Loss-S.Loss.mean())**2
print(','.join(S.loc[d.sort_values(ascending=False).index[:5],'stplc']))
