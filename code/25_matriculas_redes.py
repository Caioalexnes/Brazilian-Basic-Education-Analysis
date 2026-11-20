"""Exploratory, not in the pre-analysis plan: where the enrollment growth of high-dose municipal networks
before 2019 came from. Uses enrollment data only (Censo Escolar), no learning outcome.

1. Enrollment by municipality, year (2015 to 2025), network (federal, state, municipal, private) and stage
   (creche, pre-school, early and late grades of fundamental, secondary), schools in activity.
2. Event studies (reference 2019, specification of script 22) of ln(1 + enrollment) of the municipal and
   the state network by stage, of the whole public sector and of all networks, and of the state share of
   public fundamental enrollment. If high-dose networks grew because they took over state schools
   (municipalization), municipal enrollment rises, state enrollment falls and the public total does not move.
Inputs: DADOS/inep/microdados_censo_escolar_<year>.zip, results/22_base.csv
Outputs: results/25_matriculas_redes.csv, results/25_evento_matriculas.csv
"""
import os, sys, zipfile, importlib.util, warnings
import numpy as np
import pandas as pd
from config import DADOS, RES

AQUI = os.path.dirname(os.path.abspath(__file__))
warnings.simplefilter('ignore')
ANOS = list(range(2015, 2026))
ETAPAS = {'QT_MAT_INF_CRE': 'creche', 'QT_MAT_INF_PRE': 'pre', 'QT_MAT_FUND_AI': 'fund_ai', 'QT_MAT_FUND_AF': 'fund_af',
          'QT_MAT_MED': 'medio'}
REDES = {1: 'federal', 2: 'estadual', 3: 'municipal', 4: 'privada'}


def modulo(nome, arquivo):
    spec = importlib.util.spec_from_file_location(nome, os.path.join(AQUI, arquivo))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def ler(ano):
    z = zipfile.ZipFile(os.path.join(DADOS, 'inep', f'microdados_censo_escolar_{ano}.zip'))
    unico = [n for n in z.namelist() if n.lower().endswith(f'microdados_ed_basica_{ano}.csv')]
    tab = lambda s: [n for n in z.namelist() if n.split('/')[-1].upper().startswith(s.upper())][0]
    cols = ['CO_MUNICIPIO', 'TP_DEPENDENCIA'] + list(ETAPAS)
    if unico:
        d = pd.read_csv(z.open(unico[0]), sep=';', encoding='latin1', low_memory=False, usecols=cols + ['TP_SITUACAO_FUNCIONAMENTO'])
    else:
        d = pd.read_csv(z.open(tab(f'Tabela_Matricula_{ano}')), sep=';', encoding='latin1', low_memory=False, usecols=cols + ['CO_ENTIDADE'])
        e = pd.read_csv(z.open(tab(f'Tabela_Escola_{ano}')), sep=';', encoding='latin1', low_memory=False,
                        usecols=['CO_ENTIDADE', 'TP_SITUACAO_FUNCIONAMENTO'])
        d = d.merge(e, on='CO_ENTIDADE', how='left')
    d = d[d['TP_SITUACAO_FUNCIONAMENTO'] == 1].fillna({c: 0 for c in ETAPAS})
    g = d.groupby(['CO_MUNICIPIO', 'TP_DEPENDENCIA'])[list(ETAPAS)].sum().rename(columns=ETAPAS).reset_index()
    print(ano, len(d), flush=True)
    return g.assign(ano=ano)


if __name__ == '__main__':
    dest = os.path.join(RES, '25_matriculas_redes.csv')
    if '--ler' in sys.argv or not os.path.exists(dest):
        m = pd.concat([ler(a) for a in ANOS], ignore_index=True)
        m = m.rename(columns={'CO_MUNICIPIO': 'cod_ibge', 'TP_DEPENDENCIA': 'rede'})
        m['rede'] = m['rede'].map(REDES)
        m[['ano', 'cod_ibge', 'rede'] + list(ETAPAS.values())].to_csv(dest, sep=';', index=False)
    m = pd.read_csv(dest, sep=';')
    w = m.pivot_table(index=['cod_ibge', 'ano'], columns='rede', values=list(ETAPAS.values()), aggfunc='sum', fill_value=0)
    w.columns = [f'{e}_{r}' for e, r in w.columns]
    w = w.reset_index()
    for e in ETAPAS.values():
        w[f'{e}_publica'] = w[[c for c in (f'{e}_municipal', f'{e}_estadual', f'{e}_federal') if c in w]].sum(axis=1)
        w[f'{e}_total'] = w[f'{e}_publica'] + w.get(f'{e}_privada', 0)
    w['fund_estadual'] = w['fund_ai_estadual'] + w['fund_af_estadual']
    w['fund_publica'] = w['fund_ai_publica'] + w['fund_af_publica']
    w['parcela_estadual_fund'] = w['fund_estadual'] / w['fund_publica'].where(w['fund_publica'] > 0)
    series = ['creche_municipal', 'pre_municipal', 'fund_ai_municipal', 'fund_af_municipal', 'fund_ai_estadual', 'fund_af_estadual',
              'fund_ai_publica', 'fund_af_publica', 'fund_ai_total', 'fund_af_total', 'creche_total', 'pre_total']
    for s in series:
        w[f'ln_{s}'] = np.log1p(w[s])
    est = modulo('est', '20_estimacao.py')
    e22 = modulo('e22', '22_etapa3.py')
    W = e22.W_COLS
    b = pd.read_csv(os.path.join(RES, '22_base.csv'), sep=';')
    b = b[b['habilitado_tarde'] == 0][['ibge', 'uf', 'regiao', 'dose_previsto_2025'] + W].rename(columns={'ibge': 'cod_ibge', 'dose_previsto_2025': 'D'})
    p = w.merge(b, on='cod_ibge').rename(columns={'cod_ibge': 'id', 'regiao': 'cluster'})
    out = []
    for s in [f'ln_{s}' for s in series] + ['parcela_estadual_fund']:
        es = est.estudo_evento(p, s, 'D', W, ano_ref=2019, wild_B=999, seed=2025)
        out.append(es['tabela'].assign(serie=s, p_pre_wild=es['p_pre_wild'], unidades=es['unidades']))
    t = pd.concat(out, ignore_index=True)
    t.to_csv(os.path.join(RES, '25_evento_matriculas.csv'), sep=';', index=False, float_format='%.5f')
    with pd.option_context('display.width', 250):
        print(t.pivot(index='ano', columns='serie', values='beta').round(4).to_string())
        print(t.groupby('serie')['p_pre_wild'].first().round(3).to_string())
    m19 = p[p['ano'] == 2019]
    print('2019 means by dose group (positive vs zero):')
    print(m19.groupby(m19['D'] > 0)[series + ['parcela_estadual_fund']].mean().round(3).T.to_string())
