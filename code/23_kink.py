"""Stage 3 of the VAAT pre-analysis plan: regression kink of education spending at the 2021 threshold (K).

Plan: Section 7.6 of version 2.0, Addendum 1 (power of the kink), and items 12 to 15 of
pap/detalhes_etapa3.md, fixed before this script was run. Needs rdrobust and rddensity (Python).
Outcome: [(G2021 + G2022) - (G2018 + G2019)] / enrollment used in the 2021 VAAT, G = education spending
as in script 03, at 2021 prices. First stage: the 2021 complementation per enrolled student (reais of 2021).
Inputs: results/22_base.csv (script 22), data/ipca_1737.json
Output: results/23_kink.csv
"""
import os, json, importlib.util, warnings
import numpy as np
import pandas as pd
from config import DADOS, RES

AQUI = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('est', os.path.join(AQUI, '20_estimacao.py'))
est = importlib.util.module_from_spec(spec); spec.loader.exec_module(est)
warnings.simplefilter('ignore')


def ipca():
    d = pd.DataFrame(json.load(open(os.path.join(DADOS, 'ipca_1737.json'), encoding='utf-8'))[1:])
    d['ano'] = d['D3C'].str[:4].astype(int); d['V'] = d['V'].astype(float)
    return d.groupby('ano')['V'].mean()


def linha(nome, tipo, r):
    return dict(teste=nome, tipo=tipo, estimativa=r['repasse'] if 'repasse' in r else r['kink'], lo=r['ic'][0], hi=r['ic'][1],
                p=r['p'], h=r.get('h', np.nan), n=r.get('n', np.nan))


def fuzzy(y, x, fs, **kw):
    ok = np.isfinite(y) & np.isfinite(x) & np.isfinite(fs)
    k = est.kink(y[ok], x[ok], fs[ok], **kw)
    return dict(repasse=k['repasse'], ic=k['ic_repasse'], p=k['p_repasse'], h=k['h'], n=k['n'],
                kink_fs=k['kink_fs'], kink_y=k['kink_y'], ic_kink_y=k['ic_kink_y'])


def nitido(y, x, **kw):
    from rdrobust import rdrobust
    ok = np.isfinite(y) & np.isfinite(x)
    r = rdrobust(y[ok], x[ok], c=0.0, deriv=1, kernel='triangular', **kw)
    return dict(kink=float(np.asarray(r.coef).ravel()[0]), ic=tuple(np.asarray(r.ci, dtype=float)[2]),
                p=float(np.asarray(r.pv).ravel()[2]), h=float(np.asarray(r.bws).ravel()[0]), n=int(np.asarray(r.N_h).sum()))


if __name__ == '__main__':
    b = pd.read_csv(os.path.join(RES, '22_base.csv'), sep=';')
    b = b[b['habilitado_tarde'] == 0].reset_index(drop=True)
    ip = ipca(); f21 = ip[2021] / ip[2025]
    G = {a: b[f'gasto_aluno_{a}'] * b[f'matriculas_{a}'] * f21 for a in range(2016, 2023)}   # reais of 2021
    m = b['mat_censo']
    x = b['x'].values
    y = ((G[2021] + G[2022] - G[2018] - G[2019]) / m).values
    y_pre = ((G[2018] + G[2019] - G[2016] - G[2017]) / m).values
    fs = (b['recebido_2021'] * b['razao']).values
    rec = (b['compl_uniao_receita_2021'] / m).values
    linhas = []
    k = fuzzy(y, x, fs)
    linhas.append(linha('pass-through, main (MSE-optimal h, local linear)', 'fuzzy', k))
    linhas.append(dict(teste='first-stage kink (reais per enrolled student per unit of x)', tipo='sharp', estimativa=k['kink_fs']))
    linhas.append(dict(teste='reduced-form kink in spending', tipo='sharp', estimativa=k['kink_y'], lo=k['ic_kink_y'][0], hi=k['ic_kink_y'][1]))
    linhas.append(linha('pass-through, local quadratic', 'fuzzy', fuzzy(y, x, fs, p=2)))
    for h in (0.1, 0.2):
        linhas.append(linha(f'pass-through, h = {h}', 'fuzzy', fuzzy(y, x, fs, h=h)))
    linhas.append(linha('data check: complementation recorded as revenue in 2021', 'fuzzy', fuzzy(rec, x, fs)))
    linhas.append(linha('difference in kinks: pre-period change (2016-17 to 2018-19)', 'fuzzy', fuzzy(y_pre, x, fs)))
    linhas.append(linha('difference in kinks: main minus pre-period change', 'fuzzy', fuzzy(y - y_pre, x, fs)))
    for nome, v in (('2019 spending per student (reais of 2021)', b['gasto_aluno_2019'] * f21), ('INSE 2019', b['inse_2019']),
                    ('ln population 2020', b['ln_pop_2020']), ('ICMS share 2019', b['icms_2019'])):
        linhas.append(linha(f'predetermined: {nome}', 'sharp', nitido(v.values.astype(float), x)))
    ok = np.isfinite(y)
    pl = est.kink_placebo(y[ok], x[ok])
    for _, l in pl.iterrows():
        linhas.append(dict(teste=f'placebo threshold x = {l["limiar"]:+.2f}', tipo='sharp', estimativa=l['kink'], lo=l['ic'][0],
                           hi=l['ic'][1], p=l['p']))
    pm = est.permutacao_kink(y[ok], x[ok], h=0.2, n_placebo=200, seed=2025)
    linhas.append(dict(teste='permutation test (h = 0.2, 200 placebo thresholds)', tipo='sharp', estimativa=pm['kink'], p=pm['p'],
                       n=pm['placebos']))
    linhas.append(dict(teste='density test at x = 0', tipo='density', p=est.densidade(x)))
    t = pd.DataFrame(linhas)
    t.to_csv(os.path.join(RES, '23_kink.csv'), sep=';', index=False, float_format='%.4f')
    print(t.round(4).to_string(index=False))
