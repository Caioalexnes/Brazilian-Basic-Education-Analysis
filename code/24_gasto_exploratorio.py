"""Exploratory analyses of spending per student, not in the pre-analysis plan, run after script 22 to
understand its results. Every number here is reported as exploratory.

1. Event study of spending per student (as in script 22), with network-years outside the 1st to 99th
   percentile of each year removed, and on the balanced panel.
2. Event studies of the two parts of spending per student: ln spending and ln enrollment.
3. Mechanical benchmark for each year: the predicted money of year t per enrolled student (reais of
   2025) regressed on the dose, as the main specification. It is what the event-study coefficient of
   year t would be, relative to 2019, with full pass-through and parallel trends. Also the same money as a
   percentage of the network's 2019 spending per student, and the VAAT money actually received (with the
   2023 and 2024 adjustments) per enrolled student regressed on the dose: the first stage of the design.
4. Long differences of spending per student to 2025 from baselines before 2019 (2017, and the mean of
   2015 to 2018), with the specification of the plan.
Inputs: results/22_base.csv, data/ipca_1737.json
Output: results/24_gasto_exploratorio.csv
"""
import os, json, importlib.util, warnings
import numpy as np
import pandas as pd
from config import DADOS, RES

AQUI = os.path.dirname(os.path.abspath(__file__))
warnings.simplefilter('ignore')


def modulo(nome, arquivo):
    spec = importlib.util.spec_from_file_location(nome, os.path.join(AQUI, arquivo))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


est = modulo('est', '20_estimacao.py')
e22 = modulo('e22', '22_etapa3.py')
W = e22.W_COLS
ANOS = list(range(2015, 2026))


def evento(a, y, nome, B=999):
    p = a[['ibge', 'uf', 'regiao', 'D'] + W + [f'{y}_{t}' for t in ANOS]].melt(
        id_vars=['ibge', 'uf', 'regiao', 'D'] + W, var_name='ano', value_name='y')
    p['ano'] = p['ano'].str[-4:].astype(int)
    p = p.rename(columns={'ibge': 'id', 'regiao': 'cluster'}).dropna(subset=['y'])
    es = est.estudo_evento(p, 'y', 'D', W, ano_ref=2019, wild_B=B, seed=2025)
    return es['tabela'].assign(analise=nome, n=es['n'], unidades=es['unidades'], p_pre_wild=es['p_pre_wild'])


if __name__ == '__main__':
    r = pd.read_csv(os.path.join(RES, '22_base.csv'), sep=';')
    a = r[r['habilitado_tarde'] == 0].copy()
    a['D'] = a['dose_previsto_2025']
    out = []
    # 1
    t = a.copy()
    for ano in ANOS:
        lo, hi = t[f'gasto_aluno_{ano}'].quantile([0.01, 0.99])
        t[f'gasto_aluno_{ano}'] = t[f'gasto_aluno_{ano}'].where(t[f'gasto_aluno_{ano}'].between(lo, hi))
    out.append(evento(t, 'gasto_aluno', 'spending per student, 1st to 99th percentile of each year'))
    bal = a[a[[f'gasto_aluno_{ano}' for ano in ANOS]].notna().all(axis=1)]
    out.append(evento(bal, 'gasto_aluno', 'spending per student, balanced panel'))
    # 2
    for ano in ANOS:
        g = a[f'gasto_aluno_{ano}'] * a[f'matriculas_{ano}']
        a[f'ln_gasto_{ano}'] = np.log(g.where(g > 0))
        a[f'ln_mat_{ano}'] = np.log(a[f'matriculas_{ano}'].where(a[f'matriculas_{ano}'] > 0))
    out.append(evento(a, 'ln_gasto', 'ln spending'))
    out.append(evento(a, 'ln_mat', 'ln enrollment'))
    # 3
    ip = e22.g03.ipca_medio()
    mec = []
    for ano in range(2021, 2026):
        a['m'] = a[f'previsto_{ano}'] * a['razao'] * ip[2025] / ip[ano]
        rr = e22.ld(a.dropna(subset=['gasto_aluno_2019']), 'm', 'D')
        mec.append(dict(ano=ano, beta=rr['beta'], se=rr['se'], analise='mechanical benchmark'))
        a['m'] = a[f'recebido_ajustado_{ano}'] * a['razao'] * ip[2025] / ip[ano]
        rr = e22.ld(a.dropna(subset=['gasto_aluno_2019']), 'm', 'D')
        mec.append(dict(ano=ano, beta=rr['beta'], se=rr['se'], analise='VAAT money received per enrolled student'))
        # the same money as a percentage of the network's 2019 spending per student, comparable with ln spending x 100
        a['m'] = 100 * a[f'previsto_{ano}'] * a['razao'] * ip[2025] / ip[ano] / a['gasto_aluno_2019']
        rr = e22.ld(a.dropna(subset=['gasto_aluno_2019']), 'm', 'D')
        mec.append(dict(ano=ano, beta=rr['beta'], se=rr['se'], analise='mechanical benchmark, percent of 2019 spending'))
    out.append(pd.DataFrame(mec))
    # 4
    ld = []
    a['base_1518'] = a[[f'gasto_aluno_{ano}' for ano in range(2015, 2019)]].mean(axis=1, skipna=False)
    for nome, base in (('long difference 2019 to 2025 (plan)', 'gasto_aluno_2019'), ('long difference 2017 to 2025', 'gasto_aluno_2017'),
                       ('long difference, mean of 2015-2018 to 2025', 'base_1518')):
        a['dy'] = a['gasto_aluno_2025'] - a[base]
        rr = e22.ld(a, 'dy', 'D')
        ld.append(dict(analise=nome, beta=rr['beta'], se=rr['se'], p=rr['p'], n=rr['n']))
    out.append(pd.DataFrame(ld))
    t = pd.concat(out, ignore_index=True)
    t.to_csv(os.path.join(RES, '24_gasto_exploratorio.csv'), sep=';', index=False, float_format='%.4f')
    with pd.option_context('display.width', 200):
        for k, g in t.groupby('analise', sort=False):
            print('---', k); print(g.drop(columns='analise').dropna(axis=1, how='all').round(4).to_string(index=False))
