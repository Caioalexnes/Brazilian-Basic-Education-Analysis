"""Stage 4 of the VAAT pre-analysis plan: relative-magnitudes bounds of Rambachan and Roth (2023) on the 2025
coefficient of the event study of N, for each grade (item 6 of pap/detalhes_etapa4.md; Addendum 1).
Needs R with HonestDiD (set RSCRIPT to its Rscript). Each grade takes about a minute and a half.
Usage: python 27_honestdid.py 5    and    python 27_honestdid.py 9
Inputs: results/26_evento.csv, results/26_evento_V_<grade>.csv (script 26)
Output: results/27_honestdid_<grade>.csv
"""
import os, sys, importlib.util
import numpy as np
import pandas as pd
from config import RES

AQUI = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('est', os.path.join(AQUI, '20_estimacao.py'))
est = importlib.util.module_from_spec(spec); spec.loader.exec_module(est)

if __name__ == '__main__':
    g = int(sys.argv[1])
    ev = pd.read_csv(os.path.join(RES, '26_evento.csv'), sep=';')
    tab = ev[ev['analise'] == f'N {g}th grade'][['ano', 'beta', 'se']].reset_index(drop=True)
    V = pd.read_csv(os.path.join(RES, f'26_evento_V_{g}.csv'), sep=';', index_col=0)
    anos = [int(a) for a in V.columns]
    assert anos == tab['ano'].tolist()
    h = est.honestdid_rm(dict(anos=anos, tabela=tab, V=V.values), rscript=os.environ.get('RSCRIPT'))
    out = pd.concat([pd.DataFrame([dict(Mbar='original', lb=h['ic_original'][0], ub=h['ic_original'][1])]),
                     h['limites'].assign(Mbar=h['limites']['Mbar'].astype(str)),
                     pd.DataFrame([dict(Mbar='breakdown', lb=h['quebra'], ub=h['quebra'])])], ignore_index=True)
    out = out.assign(grade=g, beta2025=tab.set_index('ano').loc[2025, 'beta'])
    out.to_csv(os.path.join(RES, f'27_honestdid_{g}.csv'), sep=';', index=False, float_format='%.6f')
    print(out.to_string(index=False))
