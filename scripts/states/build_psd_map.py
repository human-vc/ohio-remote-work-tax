import pandas as pd

FIX = {
    'ALLEGHENY|BETHEL PARK BORO': 'ALLEGHENY|BETHEL PARK MUNICIPALITY',
    'ALLEGHENY|MONROEVILLE BORO': 'ALLEGHENY|MONROEVILLE MUNICIPALITY',
    'WESTMORELAND|MURRYSVILLE BORO': 'WESTMORELAND|MURRYSVILLE MUNICIPALITY',
    'LUZERNE|WILKES BARRE CITY': 'LUZERNE|WILKESBARRE CITY',
    'LUZERNE|WILKES BARRE TWP': 'LUZERNE|WILKESBARRE TWP',
    'VENANGO|OIL CITY': 'VENANGO|OIL CITY CITY',
    'VENANGO|OILCREEK TWP': 'VENANGO|OIL CREEK TWP',
    'ERIE|LE BOEUF TWP': 'ERIE|LEBOEUF TWP',
    'LACKAWANNA|LAPLUME TWP': 'LACKAWANNA|LA PLUME TWP',
    'CAMBRIA|NANTY GLO BORO': 'CAMBRIA|NANTYGLO BORO',
    'SUSQUEHANNA|UNIONDALE BORO': 'SUSQUEHANNA|UNION DALE BORO',
    'SCHUYLKILL|UPPER MAHANTANGO TWP': 'SCHUYLKILL|UPPER MAHANTONGO TWP',
}


def norm(s):
    return (s.str.upper().str.replace(r'\s*\(.*', '', regex=True)
            .str.replace(r'\bBOROUGH\b', 'BORO', regex=True).str.replace(r'\bTOWNSHIP\b', 'TWP', regex=True)
            .str.replace(r'\bSAINT\b', 'ST', regex=True).str.replace(r'\bMOUNT\b', 'MT', regex=True)
            .str.replace(r'[^A-Z0-9 ]', '', regex=True).str.replace(r'\s+', ' ', regex=True).str.strip())


def sdnorm(s):
    return (s.str.upper().str.replace(r'\bSCHOOL DISTRICT\b|\bS D\b|\bSD\b', '', regex=True)
            .str.replace(r'[^A-Z0-9 ]', ' ', regex=True).str.replace(r'\bAREA\b', ' AREA ', regex=True)
            .str.replace(r'\bTWP\b', 'TOWNSHIP', regex=True).str.replace(r'\bMT\b', 'MOUNT', regex=True)
            .str.replace(r'\s+', ' ', regex=True).str.strip())


reg = pd.read_csv('data/pennsylvania/eit_register_2023_07_clean.csv', dtype={'psd': str})
reg['k'] = reg.county.str.upper() + '|' + norm(reg.muni.str.replace(r'\bBORO\b', 'BOROUGH', regex=True)
                                              .str.replace(r'\bTWP\b', 'TOWNSHIP', regex=True))
reg['k'] = reg.k.replace(FIX)
reg['sdk'] = sdnorm(reg.sd)
reg.loc[reg.muni == 'PHILADELPHIA CITY', 'tot'] = 3.75
reg.loc[reg.muni == 'PHILADELPHIA CITY', 'mr'] = 3.75

xw = pd.read_csv('data/raw/lodes/pa_xwalk.csv.gz', dtype=str, usecols=['tabblk2020', 'ctyname', 'ctycsubname'])
xw['k'] = xw.ctyname.str.upper().str.replace(' COUNTY, PA', '', regex=False) + '|' + norm(xw.ctycsubname)
baf = pd.read_csv('data/raw/baf/BlockAssign_ST42_PA_SDUNI.txt', sep='|', dtype=str).rename(columns={'BLOCKID': 'tabblk2020'})
gz = pd.read_csv('data/raw/baf/2020_Gaz_unsd_national.txt', sep='\t', dtype=str)
gz.columns = [c.strip() for c in gz.columns]
gz = gz[gz.USPS == 'PA']
gz['DISTRICT'] = gz.GEOID.str[2:]
gz['sdk'] = sdnorm(gz.NAME)
xw = xw.merge(baf, on='tabblk2020', how='left').merge(gz[['DISTRICT', 'sdk']], on='DISTRICT', how='left')

one = reg.groupby('k').filter(lambda g: len(g) == 1).set_index('k').psd
multi = reg.groupby('k').filter(lambda g: len(g) > 1).set_index(['k', 'sdk']).psd
psd = xw.k.map(one)
m2 = pd.Series(list(zip(xw.k, xw.sdk))).map(multi.to_dict())
psd = psd.fillna(pd.Series(m2.values, index=xw.index))
xw['psd'] = psd
xw[['tabblk2020', 'k', 'sdk', 'psd']].to_csv('output/states/block_psd_map.csv.gz', index=False)
print('blocks', len(xw), 'mapped', round(xw.psd.notna().mean(), 4))
print('unmatched munis in register', sorted(set(reg.k) - set(xw.k))[:20])
reg.to_csv('output/states/psd_rates_2023_07.csv', index=False)
