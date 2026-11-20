"""School inputs of each municipal network, 2019, 2023 and 2025 (mechanisms of the VAAT pre-analysis plan).

From the Censo Escolar school file (schools in activity; from 2025 the counts come in separate tables of
enrollments, classes and teachers, joined by school code):
  - creche and pre-school enrollment of municipal schools, plus that of private schools under agreement
    with the municipality (as in script 02), and the full-time share of each;
  - enrollment and full-time share of ensino fundamental, municipal schools;
  - students per class in the early grades of fundamental (enrollment over classes), municipal schools;
  - teachers per 100 students: teacher counts of each school (QT_DOC_BAS; a teacher who works in two
    schools is counted in both) over basic-education enrollment, municipal schools.
From Inep's educational indicators by municipality, municipal network, all locations:
  - share of teachers with higher education (DSU), early childhood and fundamental. Up to 2019 Inep
    computes it over teaching posts (funções docentes), later over teachers;
  - mean daily class hours (HAD), creche, pre-school and early grades of fundamental.
Inputs: data/inep/microdados_censo_escolar_<year>.zip, data/inep/indicadores/{DSU,HAD}_<year>_MUNICIPIOS.zip
Output: results/16_insumos.csv (one row per municipality and year)
"""
import os, zipfile
import numpy as np
import pandas as pd
from config import DADOS, RES

ANOS = (2019, 2023, 2025)
MAT = ['QT_MAT_BAS', 'QT_MAT_INF_CRE', 'QT_MAT_INF_PRE', 'QT_MAT_INF_CRE_INT', 'QT_MAT_INF_PRE_INT',
       'QT_MAT_FUND', 'QT_MAT_FUND_INT', 'QT_MAT_FUND_AI']


def tabela(z, prefixo):
    return [n for n in z.namelist() if n.split('/')[-1].upper().startswith(prefixo.upper())][0]


def censo(ano):
    z = zipfile.ZipFile(os.path.join(DADOS, 'inep', f'microdados_censo_escolar_{ano}.zip'))
    unico = [n for n in z.namelist() if n.lower().endswith(f'microdados_ed_basica_{ano}.csv')]
    ler = lambda nome, cols: pd.read_csv(z.open(nome), sep=';', encoding='latin1', low_memory=False, usecols=cols)
    if unico:
        cab = pd.read_csv(z.open(unico[0]), sep=';', encoding='latin1', nrows=0).columns
        conv = ['IN_PODER_PUBLICO_PARCERIA', 'TP_PODER_PUBLICO_PARCERIA'] if 'TP_PODER_PUBLICO_PARCERIA' in cab else ['IN_CONVENIADA_PP', 'TP_CONVENIO_PODER_PUBLICO']
        d = ler(unico[0], ['CO_MUNICIPIO', 'TP_DEPENDENCIA', 'TP_SITUACAO_FUNCIONAMENTO', 'QT_TUR_FUND_AI', 'QT_DOC_BAS'] + MAT + conv)
    else:
        m = tabela(z, f'Tabela_Matricula_{ano}')
        cab = pd.read_csv(z.open(m), sep=';', encoding='latin1', nrows=0).columns
        conv = ['IN_PODER_PUBLICO_PARCERIA', 'TP_PODER_PUBLICO_PARCERIA'] if 'TP_PODER_PUBLICO_PARCERIA' in cab else ['IN_CONVENIADA_PP', 'TP_CONVENIO_PODER_PUBLICO']
        d = ler(m, ['CO_ENTIDADE', 'CO_MUNICIPIO', 'TP_DEPENDENCIA'] + MAT + conv)
        for nome, cols in ((f'Tabela_Escola_{ano}', ['TP_SITUACAO_FUNCIONAMENTO']), (f'Tabela_Turma_{ano}', ['QT_TUR_FUND_AI']),
                           (f'Tabela_Docente_{ano}', ['QT_DOC_BAS'])):
            t = ler(tabela(z, nome), ['CO_ENTIDADE'] + cols)
            assert t['CO_ENTIDADE'].is_unique
            n = len(d); d = d.merge(t, on='CO_ENTIDADE', how='left'); assert len(d) == n
    d = d[d['TP_SITUACAO_FUNCIONAMENTO'] == 1].fillna({c: 0 for c in MAT + ['QT_TUR_FUND_AI', 'QT_DOC_BAS']})
    mun = d[d['TP_DEPENDENCIA'] == 3].groupby('CO_MUNICIPIO')[MAT + ['QT_TUR_FUND_AI', 'QT_DOC_BAS']].sum()
    conv_ = d[(d['TP_DEPENDENCIA'] == 4) & (d[conv[0]] == 1) & d[conv[1]].isin([1, 3])]
    conv_ = conv_.groupby('CO_MUNICIPIO')[['QT_MAT_INF_CRE', 'QT_MAT_INF_PRE', 'QT_MAT_INF_CRE_INT', 'QT_MAT_INF_PRE_INT']].sum()
    conv_ = conv_.reindex(mun.index.union(conv_.index)).fillna(0)
    mun = mun.reindex(conv_.index).fillna(0)
    r = pd.DataFrame(index=mun.index)
    for e, E in (('creche', 'CRE'), ('pre', 'PRE')):
        r[f'mat_{e}_municipal'] = mun[f'QT_MAT_INF_{E}']
        r[f'mat_{e}'] = mun[f'QT_MAT_INF_{E}'] + conv_[f'QT_MAT_INF_{E}']
        r[f'integral_{e}'] = (mun[f'QT_MAT_INF_{E}_INT'] + conv_[f'QT_MAT_INF_{E}_INT']) / r[f'mat_{e}'].replace(0, np.nan)
    r['mat_fundamental'] = mun['QT_MAT_FUND']
    r['integral_fundamental'] = mun['QT_MAT_FUND_INT'] / mun['QT_MAT_FUND'].replace(0, np.nan)
    r['alunos_turma_ai'] = mun['QT_MAT_FUND_AI'] / mun['QT_TUR_FUND_AI'].replace(0, np.nan)
    r['docentes_100_alunos'] = 100 * mun['QT_DOC_BAS'] / mun['QT_MAT_BAS'].replace(0, np.nan)
    r.index.name = 'cod_ibge'
    return r.reset_index().assign(ano=ano)


def indicador(sigla, ano, cols):
    z = zipfile.ZipFile(os.path.join(DADOS, 'inep', 'indicadores', f'{sigla}_{ano}_MUNICIPIOS.zip'))
    nome = [n for n in z.namelist() if n.lower().endswith(('.xlsx', '.xls'))][0]
    x = pd.read_excel(z.open(nome), header=None)
    i = x.index[x.iloc[:, 0].astype(str).str.strip() == 'NU_ANO_CENSO'][0]
    x.columns = x.iloc[i].astype(str).str.strip(); x = x.iloc[i + 1:]
    x = x[(x['NO_CATEGORIA'] == 'Total') & (x['NO_DEPENDENCIA'] == 'Municipal')]
    out = pd.DataFrame({'cod_ibge': pd.to_numeric(x['CO_MUNICIPIO'], errors='coerce').astype('Int64')})
    for c, novo in cols.items():
        out[novo] = pd.to_numeric(x[c].replace('--', np.nan), errors='coerce').values
    return out.dropna(subset=['cod_ibge']).assign(ano=ano)


if __name__ == '__main__':
    partes = []
    for ano in ANOS:
        c = censo(ano)
        dsu = indicador('DSU', ano, {'ED_INF_CAT_0': 'superior_infantil', 'FUN_CAT_0': 'superior_fundamental'})
        had = indicador('HAD', ano, {'CRE_CAT_0': 'horas_creche', 'PRE_CAT_0': 'horas_pre', 'FUN_AI_CAT_0': 'horas_fundamental_ai'})
        c = c.merge(dsu, on=['cod_ibge', 'ano'], how='left').merge(had, on=['cod_ibge', 'ano'], how='left')
        partes.append(c)
        print(ano, len(c), c.drop(columns=['cod_ibge', 'ano']).notna().mean().round(3).to_dict(), flush=True)
    r = pd.concat(partes, ignore_index=True)
    r = r[['ano', 'cod_ibge'] + [k for k in r.columns if k not in ('ano', 'cod_ibge')]].sort_values(['ano', 'cod_ibge'])
    r.to_csv(os.path.join(RES, '16_insumos.csv'), sep=';', index=False, float_format='%.4f')
    print(r.groupby('ano').median(numeric_only=True).drop(columns='cod_ibge').round(2).T.to_string())
