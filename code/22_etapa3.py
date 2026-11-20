"""Stage 3 of the VAAT pre-analysis plan: education spending (P1), spending by stage and school inputs
(S2), robustness and heterogeneity of P1, and an exploratory event study of spending.

Plan: doi:10.5281/zenodo.24391651 (version 2.0) and Addendum 1 (doi:10.5281/zenodo.24394910).
Implementation details fixed before this script was run: pap/detalhes_etapa3.md (items 1 to 11 and 16).
The kink (items 12 to 15) is in script 23, which needs rdrobust.
Inputs: results/13_vaat_redes.csv, results/02_matriculas.csv, results/16_insumos.csv,
        data/siconfi/dca_<year>.csv, data/siconfi/receitas_<2019, 2021>.csv, data/pop_2020.json,
        data/inep/INSE_2019_MUNICIPIOS.xlsx, data/ibge_municipios.json, data/ipca_1737.json
Outputs: results/22_base.csv (one row per network: dose, covariates, outcomes)
         results/22_p1.csv, results/22_p1_curva.csv, results/22_p1_robustez.csv,
         results/22_p1_heterogeneidade.csv, results/22_s2.csv, results/22_evento_gasto.csv
"""
import os, json, warnings, importlib.util
import numpy as np
import pandas as pd
from scipy import stats
from config import DADOS, RES

AQUI = os.path.dirname(os.path.abspath(__file__))
warnings.simplefilter('ignore', pd.errors.PerformanceWarning)


def modulo(nome, arquivo):
    spec = importlib.util.spec_from_file_location(nome, os.path.join(AQUI, arquivo))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


est = modulo('est', '20_estimacao.py')
g03 = modulo('g03', '03_gasto_ideb.py')

ANOS = range(2015, 2026)
NORDESTE = {'MA', 'PI', 'CE', 'RN', 'PB', 'PE', 'AL', 'SE', 'BA'}
P75 = 5.0130   # 75th percentile of the positive dose (results/13_diagnosticos.csv)
B = 999


def gasto_etapas(ano):
    """Spending as in script 03, plus subfunctions 12.365 and 12.361 (zero if absent, item 2)."""
    g = g03.gasto(ano)
    d = pd.read_csv(os.path.join(DADOS, 'siconfi', f'dca_{ano}.csv'), sep=';')
    for sub, nome in (('12.365', 'g_infantil'), ('12.361', 'g_fundamental')):
        g[nome] = d[d['conta'].str.startswith(sub)].groupby('cod_ibge')['valor'].sum().reindex(g.index).fillna(0.0)
    return g


def base():
    r = pd.read_csv(os.path.join(RES, '13_vaat_redes.csv'), sep=';')
    mun = json.load(open(os.path.join(DADOS, 'ibge_municipios.json')))
    r['regiao'] = r['ibge'].map({m['id']: m['regiao-imediata']['id'] for m in mun})
    uf = r['ibge'].map({m['id']: m['regiao-imediata']['regiao-intermediaria']['UF']['sigla'] for m in mun})
    assert (uf[r['uf'].notna()] == r.loc[r['uf'].notna(), 'uf']).all()
    r['uf'] = r['uf'].fillna(uf)   # the 105 late recipients have no state in script 13
    r['razao'] = r['mat_vaat'] / r['mat_censo']
    ip = g03.ipca_medio()
    mat = pd.read_csv(os.path.join(RES, '02_matriculas.csv'), sep=';').pivot(index='cod_ibge', columns='ano', values='matriculas')
    for a in ANOS:
        g = gasto_etapas(a)
        f = ip[2025] / ip[a]
        m = mat[a].where(mat[a] > 0)
        r[f'gasto_aluno_{a}'] = r['ibge'].map(g['gasto'] / m * f)
        r[f'g_infantil_{a}'] = r['ibge'].map(g['g_infantil'] * f)
        r[f'g_fundamental_{a}'] = r['ibge'].map(g['g_fundamental'] * f)
        r[f'matriculas_{a}'] = r['ibge'].map(mat[a])
    ins = pd.read_csv(os.path.join(RES, '16_insumos.csv'), sep=';')
    for a in (2019, 2023, 2025):
        i = ins[ins['ano'] == a].set_index('cod_ibge')
        for c in i.columns.drop('ano'):
            r[f'{c}_{a}'] = r['ibge'].map(i[c])
        r[f'gasto_infantil_aluno_{a}'] = r[f'g_infantil_{a}'] / (r[f'mat_creche_{a}'] + r[f'mat_pre_{a}']).where(lambda v: v > 0)
        r[f'gasto_fundamental_aluno_{a}'] = r[f'g_fundamental_{a}'] / r[f'mat_fundamental_{a}'].where(lambda v: v > 0)
        for c in ('mat_creche', 'mat_pre'):
            r[f'ln_{c}_{a}'] = np.log1p(r[f'{c}_{a}'])
    # covariates (Section 3 and item 5)
    r['inse_2019'] = r['ibge'].map(g03.inse(2019))
    pop = json.load(open(os.path.join(DADOS, 'pop_2020.json')))[1:]
    r['ln_pop_2020'] = np.log(r['ibge'].map({int(p['D1C']): pd.to_numeric(p['V'], errors='coerce') for p in pop}))
    rc = pd.read_csv(os.path.join(DADOS, 'siconfi', 'receitas_2019.csv'), sep=';').pivot_table(
        index='cod_ibge', columns='cod_conta', values='valor', aggfunc='sum')
    r['icms_2019'] = r['ibge'].map(rc['RO1.7.2.8.01.1.0'] / rc['RO1.0.0.0.00.0.0'])
    # data check of the kink (item 13): the Union's complementation recorded as revenue in 2021, zero if the
    # municipality reported Annex I-C but not this account
    r21 = pd.read_csv(os.path.join(DADOS, 'siconfi', 'receitas_2021.csv'), sep=';').pivot_table(
        index='cod_ibge', columns='cod_conta', values='valor', aggfunc='sum')
    r['compl_uniao_receita_2021'] = r['ibge'].map(r21['RO1.7.1.8.09.0.0'].fillna(0.0))
    for c in ('inse_2019', 'icms_2019'):
        r[f'{c}_falta'] = r[c].isna().astype(float)
        r[f'{c}_imp'] = r[c].fillna(r.groupby('uf')[c].transform('mean'))
    r['nordeste'] = r['uf'].isin(NORDESTE).astype(float)
    return r


W_COLS = ['inse_2019_imp', 'inse_2019_falta', 'ln_pop_2020', 'icms_2019_imp', 'icms_2019_falta']


def p_valor(b, se, G):
    return 2 * (1 - stats.t.cdf(abs(b / se), G - 1))


def ld(s, y, dose, W=W_COLS, cluster='regiao', w=None, extra=None):
    """Long difference; extra: columns placed before W whose coefficients are also returned."""
    cols = (extra or []) + list(W)
    s = s.dropna(subset=[y, dose] + cols)
    Wm = s[cols].values if cols else None
    r = est.diferenca_longa(s[y].values, s[dose].values, Wm, s['uf'].values,
                            cluster=None if cluster is None else s[cluster].values, w=None if w is None else s[w].values)
    G = r['clusters']
    return dict(beta=r['beta'], se=r['se'], p=p_valor(r['beta'], r['se'], G), n=r['n'], clusters=G,
                tratados=int((s[dose] > 0).sum()), coef=r['coef'], V=r['V'])


def bh(p):
    p = np.asarray(p, float); n = len(p); o = np.argsort(p)
    q = np.minimum.accumulate((p[o] * n / np.arange(1, n + 1))[::-1])[::-1]
    out = np.empty(n); out[o] = np.minimum(q, 1)
    return out


def linha(nome, r, escala=P75):
    t = stats.t.ppf(0.975, r['clusters'] - 1) if r['clusters'] < r['n'] else 1.96
    return dict(especificacao=nome, beta=r['beta'], se=r['se'], lo=r['beta'] - t * r['se'], hi=r['beta'] + t * r['se'],
                p=r['p'], beta_p75=r['beta'] * escala, lo_p75=(r['beta'] - t * r['se']) * escala,
                hi_p75=(r['beta'] + t * r['se']) * escala, n=r['n'], tratados=r['tratados'], clusters=r['clusters'])


if __name__ == '__main__':
    r = base()
    r.to_csv(os.path.join(RES, '22_base.csv'), sep=';', index=False, float_format='%.6f')
    a = r[r['habilitado_tarde'] == 0].copy()
    a['dy'] = a['gasto_aluno_2025'] - a['gasto_aluno_2019']
    a['D'] = a['dose_previsto_2025']
    print('main sample', len(a), '| P1 observed', a['dy'].notna().sum(), '| covariates missing:',
          {c: int(a[c].isna().sum()) for c in ('inse_2019', 'ln_pop_2020', 'icms_2019')}, flush=True)

    # benchmark computed from treatment data only (not an outcome): the predicted 2025 money per enrolled student,
    # in 2025 reais, regressed on the dose with the same specification. Beta over this is the pass-through.
    a['mecanico'] = a['previsto_2025'] * a['razao']
    mec = ld(a.dropna(subset=['dy']), 'mecanico', 'D')

    # P1: beta and ATT^o (item 7)
    p1 = ld(a, 'dy', 'D')
    s = a.dropna(subset=['dy'] + W_COLS)
    dr = est.resposta_dose(s['dy'].values, s['D'].values, s[W_COLS].values, s['uf'].values, s['regiao'].values, B=B, seed=2025)
    linhas = [linha('beta', p1), dict(especificacao='ATT^o', beta=dr['att_o'], se=dr['se_att_o'], lo=dr['ic_att_o'][0],
                                       hi=dr['ic_att_o'][1], n=dr['n'], tratados=dr['tratados']),
              dict(especificacao='mean of h prime', beta=dr['acrt'], se=dr['se_acrt'], lo=dr['ic_acrt'][0], hi=dr['ic_acrt'][1],
                   n=dr['n'], tratados=dr['tratados']),
              dict(especificacao='mechanical benchmark: predicted 2025 money per enrolled student', beta=mec['beta'], se=mec['se'],
                   n=mec['n'], tratados=mec['tratados'])]
    pd.DataFrame(linhas).to_csv(os.path.join(RES, '22_p1.csv'), sep=';', index=False, float_format='%.4f')
    dr['curva'].to_csv(os.path.join(RES, '22_p1_curva.csv'), sep=';', index=False, float_format='%.4f')
    print('--- P1'); print(pd.DataFrame(linhas).round(3).to_string(index=False), flush=True)

    # robustness (item 9)
    rb = [linha('main', p1)]
    rb.append(linha('1 no covariates', ld(a, 'dy', 'D', W=[])))
    a['gasto_2019'] = a['gasto_aluno_2019']
    rb.append(linha('3 2019 level as covariate', ld(a, 'dy', 'D', W=W_COLS + ['gasto_2019'])))
    rb.append(linha('4 excluding Ceara', ld(a[a['uf'] != 'CE'], 'dy', 'D')))
    lo, hi = a['dy'].quantile([0.01, 0.99])
    rb.append(linha('5 trimming 1% tails of the change', ld(a[a['dy'].between(lo, hi)], 'dy', 'D')))
    rb.append(linha('6 zero-dose networks only if x <= 0.3', ld(a[(a['D'] > 0) | (a['x'] <= 0.3)], 'dy', 'D')))
    a['dose_por_matricula'] = a['D'] * a['razao']
    for nome, col, esc in (('7a dose from money received, with adjustments', 'dose_recebido_ajustado_2025', None),
                           ('7b g_t from Fundeb revenue growth', 'dose_previsto_alt_2025', None),
                           ('7c dose in nominal reais', 'dose_previsto', None),
                           ('7d dose per enrolled student', 'dose_por_matricula', None)):
        rb.append(linha(nome, ld(a, 'dy', col), escala=a.loc[a[col] > 0, col].quantile(0.75)))
    t = r.copy()
    t['dy'] = t['gasto_aluno_2025'] - t['gasto_aluno_2019']
    t['D8'] = np.where(t['habilitado_tarde'] == 1, t['dose_recebido_ajustado_2025'], t['dose_previsto_2025'])
    rb.append(linha('8 including the 105 late recipients, actual dose', ld(t, 'dy', 'D8')))
    a['peso'] = a['matriculas_2019']
    rb.append(linha('9 weighted by 2019 enrollment', ld(a, 'dy', 'D', w='peso')))
    rb.append(linha('10 heteroskedasticity-robust errors, no clustering', ld(a, 'dy', 'D', cluster=None)))
    rb = pd.DataFrame(rb)
    rb.to_csv(os.path.join(RES, '22_p1_robustez.csv'), sep=';', index=False, float_format='%.4f')
    print('--- P1 robustness'); print(rb.round(3).to_string(index=False), flush=True)

    # heterogeneity (item 11)
    med = a['inse_2019'].median()
    a['inse_baixo'] = (a['inse_2019'] < med).astype(float)
    a['iei_alto'] = (a['iei_medio'] > a['iei_medio'].median()).astype(float)
    het = []
    for nome, h in (('Northeast', 'nordeste'), ('INSE 2019 below the median', 'inse_baixo'), ('IEI share above the median', 'iei_alto')):
        a['Dxh'] = a['D'] * a[h]
        rr = ld(a, 'dy', 'D', extra=['Dxh', h])
        G = rr['clusters']; V = rr['V']
        b0, b1 = rr['coef'][0], rr['coef'][0] + rr['coef'][1]
        se1 = np.sqrt(V[0, 0] + V[1, 1] + 2 * V[0, 1])
        het.append(dict(grupo=nome, beta_fora=b0, se_fora=np.sqrt(V[0, 0]), beta_dentro=b1, se_dentro=se1,
                        diferenca=rr['coef'][1], se_diferenca=np.sqrt(V[1, 1]), p_diferenca=p_valor(rr['coef'][1], np.sqrt(V[1, 1]), G),
                        n=rr['n'], tratados_no_grupo=int(((a[h] == 1) & (a['D'] > 0) & a['dy'].notna()).sum())))
    het = pd.DataFrame(het)
    het.to_csv(os.path.join(RES, '22_p1_heterogeneidade.csv'), sep=';', index=False, float_format='%.4f')
    print('--- P1 heterogeneity'); print(het.round(3).to_string(index=False), flush=True)

    # S2 (items 2, 3, 4 and 8)
    s2 = []
    niveis = ['gasto_infantil_aluno', 'gasto_fundamental_aluno', 'ln_mat_creche', 'ln_mat_pre', 'integral_creche', 'integral_pre',
              'integral_fundamental', 'alunos_turma_ai', 'docentes_100_alunos', 'superior_infantil', 'superior_fundamental',
              'horas_creche', 'horas_pre', 'horas_fundamental_ai']
    for ano, dose in ((2025, 'dose_previsto_2025'), (2023, 'dose_previsto_2023_2025')):
        for c in niveis:
            a['dy_s2'] = a[f'{c}_{ano}'] - a[f'{c}_2019']
            rr = ld(a, 'dy_s2', dose)
            ss = a.dropna(subset=['dy_s2'] + W_COLS)
            d2 = est.resposta_dose(ss['dy_s2'].values, ss[dose].values, ss[W_COLS].values, ss['uf'].values, ss['regiao'].values,
                                   B=B, seed=2025)
            esc = a.loc[a[dose] > 0, dose].quantile(0.75)
            l = linha(f'{c} {ano}', rr, escala=esc)
            l.update(desfecho=c, ano=ano, att_o=d2['att_o'], att_o_lo=d2['ic_att_o'][0], att_o_hi=d2['ic_att_o'][1],
                     media_2019=a.loc[a['dy_s2'].notna(), f'{c}_2019'].mean())
            s2.append(l)
    s2 = pd.DataFrame(s2)
    s2['q_bh'] = bh(s2['p'])
    s2.to_csv(os.path.join(RES, '22_s2.csv'), sep=';', index=False, float_format='%.5f')
    print('--- S2'); print(s2[['especificacao', 'beta', 'se', 'p', 'q_bh', 'beta_p75', 'att_o', 'att_o_lo', 'att_o_hi', 'media_2019', 'n']]
                       .round(4).to_string(index=False), flush=True)

    # exploratory event study of spending per student (item 16)
    p = a[['ibge', 'uf', 'regiao', 'D'] + W_COLS + [f'gasto_aluno_{y}' for y in ANOS]].melt(
        id_vars=['ibge', 'uf', 'regiao', 'D'] + W_COLS, var_name='ano', value_name='gasto')
    p['ano'] = p['ano'].str[-4:].astype(int)
    p = p.rename(columns={'ibge': 'id', 'regiao': 'cluster'})
    es = est.estudo_evento(p, 'gasto', 'D', W_COLS, ano_ref=2019, wild_B=B, seed=2025)
    tab = es['tabela'].assign(n=es['n'], unidades=es['unidades'], F_pre=es['F_pre'], p_pre=es['p_pre'], p_pre_wild=es['p_pre_wild'])
    tab.to_csv(os.path.join(RES, '22_evento_gasto.csv'), sep=';', index=False, float_format='%.4f')
    print('--- event study of spending (exploratory)'); print(tab.round(3).to_string(index=False), flush=True)
