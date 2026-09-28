import subprocess,os,pandas as pd,re,sys
S=pd.read_csv('output/revenue/sample_primary_with_controls.csv',dtype=str)
rows=[]
for col,vals in (('county',S.county.value_counts().index),('metro',S.metro.value_counts().index)):
    for v in vals:
        o=subprocess.run([sys.executable,'scripts/revenue/model.py','0'],capture_output=True,text=True,env={**os.environ,'EXCLUDE_COL':col,'EXCLUDE_VAL':v}).stdout
        m=re.search(r'LOO_GAIN_POST ([-\d.e]+) ([-\d.e]+) (\d+)',o)
        if m: rows.append((col,v,int((S[col]==v).sum()),float(m[1]),float(m[2])))
R=pd.DataFrame(rows,columns=['drop','value','places_dropped','gain_post','se'])
R.to_csv('output/revenue/leave_one_out.csv',index=False)
print(R.groupby('drop').gain_post.agg(['min','max','count']).round(3))
