"""Stage 4 of the VAAT pre-analysis plan: learning (P2), with its event study, robustness, heterogeneity,
within-municipality comparison and negative control, and the secondary learning family (S1).

Plan: doi:10.5281/zenodo.24391651 (version 2.0) and Addendum 1 (doi:10.5281/zenodo.24394910).
Implementation details fixed before this script was run: pap/detalhes_etapa4.md. HonestDiD is in
script 27, which reads the event-study coefficients and covariances saved here.
Inputs: results/22_base.csv, data/inep/divulgacao_anos_{iniciais,finais}_municipios_2025/*.xlsx,
        data/inep/INSE_2023_municipios.xlsx
Outputs: results/26_p2.csv, 26_p2_curva.csv, 26_p2_robustez.csv, 26_p2_heterogeneidade.csv, 26_evento.csv,
         26_evento_V_<grade>.csv, 26_dentro.csv, 26_s1.csv
"""
import os, importlib.util, warnings
import numpy as np
import pandas as pd
from scipy import stats
from config import DADOS, RES

AQUI = os.path.dirname(os.path.abspath(__file__))
warnings.simplefilter('ignore')


def modulo(nome, arquivo):
    spec = importlib.util.spec_from_file_location(nome, os.path.join(AQUI, arquivo))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


e22 = modulo('e22', '22_etapa3.py')
est, g03, ld, linha, bh, W, p_valor = e22.est, e22.g03, e22.ld, e22.linha, e22.bh, e22.W_COLS, e22.p_valor
B = 999
ANOS = list(range(2005, 2026, 2))
ARQ = {5: 'divulgacao_anos_iniciais_municipios_2025', 9: 'divulgacao_anos_finais_municipios_2025'}
VARS = {'N': 'VL_NOTA_MEDIA', 'mat': 'VL_NOTA_MATEMATICA', 'por': 'VL_NOTA_PORTUGUES', 'P': 'VL_INDICADOR_REND', 'ideb': 'VL_OBSERVADO'}
SD_N = {5: 0.5069, 9: 0.5740}                         # student SD per point of N (item 2)
SD_DISC = {(5, 'mat'): 53.4220, (5, 'por'): 52.4237, (9, 'mat'): 53.0660, (9, 'por'): 51.4711}   # script 09


def ideb():
    """Columns <var>_<grade>_<rede>_<year> for the municipal and state networks."""
    partes = []
    for g, nome in ARQ.items():
        x = pd.read_excel(os.path.join(DADOS, 'inep', nome, nome + '.xlsx'), header=9)
        x['ibge'] = pd.to_numeric(x['CO_MUNICIPIO'], errors='coerce')
        for rede, sig in (('Municipal', 'mun'), ('Estadual', 'est')):
            s = x[x['REDE'] == rede].set_index('ibge')
            cols = {f'{v}_{g}_{sig}_{a}': pd.to_numeric(s[f'{c}_{a}'], errors='coerce') for v, c in VARS.items() for a in ANOS}
            partes.append(pd.DataFrame(cols))
    return pd.concat(partes, axis=1)


def holm(p):
    p = np.asarray(p, float); n = len(p); o = np.argsort(p)
    adj = np.minimum(1, np.maximum.accumulate(p[o] * (n - np.arange(n))))
    out = np.empty(n); out[o] = adj
    return out


def robustez(a, t, dy, base_col, nome):
    """Robustness checks 1 and 3 to 10 of Section 8, as in script 22."""
    rb = [linha('main', ld(a, dy, 'D')), linha('1 no covariates', ld(a, dy, 'D', W=[])),
          linha('3 2019 level as covariate', ld(a, dy, 'D', W=W + [base_col])),
          linha('4 excluding Ceara', ld(a[a['uf'] != 'CE'], dy, 'D'))]
    lo, hi = a[dy].quantile([0.01, 0.99])
    rb.append(linha('5 trimming 1% tails of the change', ld(a[a[dy].between(lo, hi)], dy, 'D')))
    rb.append(linha('6 zero-dose networks only if x <= 0.3', ld(a[(a['D'] > 0) | (a['x'] <= 0.3)], dy, 'D')))
    for n, col in (('7a dose from money received, with adjustments', 'dose_recebido_ajustado_2025'),
                   ('7b g_t from Fundeb revenue growth', 'dose_previsto_alt_2025'), ('7c dose in nominal reais', 'dose_previsto'),
                   ('7d dose per enrolled student', 'dose_por_matricula')):
        rb.append(linha(n, ld(a, dy, col), escala=a.loc[a[col] > 0, col].quantile(0.75)))
    rb.append(linha('8 including the 105 late recipients, actual dose', ld(t, dy, 'D8')))
    rb.append(linha('9 weighted by 2019 enrollment', ld(a, dy, 'D', w='matriculas_2019')))
    rb.append(linha('10 heteroskedasticity-robust errors, no clustering', ld(a, dy, 'D', cluster=None)))
    return pd.DataFrame(rb).assign(desfecho=nome)


def evento(a, col, nome, balanceado=False):
    cols = [f'{col}_{y}' for y in ANOS]
    s = a[a[cols].notna().all(axis=1)] if balanceado else a
    p = s[['ibge', 'uf', 'regiao', 'D'] + W + cols].melt(id_vars=['ibge', 'uf', 'regiao', 'D'] + W, var_name='ano', value_name='y')
    p['ano'] = p['ano'].str[-4:].astype(int)
    p = p.rename(columns={'ibge': 'id', 'regiao': 'cluster'}).dropna(subset=['y'])
    es = est.estudo_evento(p, 'y', 'D', W, ano_ref=2019, wild_B=B, seed=2025)
    tl = est.tendencia_linear(es)
    tab = es['tabela'].assign(analise=nome, unidades=es['unidades'], n=es['n'], F_pre=es['F_pre'], p_pre=es['p_pre'],
                              p_pre_wild=es['p_pre_wild'], beta2025_menos_tendencia=tl['beta_ajustado'], se_menos_tendencia=tl['se'])
    return tab, es


if __name__ == '__main__':
    r = pd.read_csv(os.path.join(RES, '22_base.csv'), sep=';')
    r = r.join(ideb(), on='ibge')
    r['inse_2023'] = r['ibge'].map(g03.inse(2023))
    r['D'] = r['dose_previsto_2025']
    r['dose_por_matricula'] = r['D'] * r['razao']
    r['D8'] = np.where(r['habilitado_tarde'] == 1, r['dose_recebido_ajustado_2025'], r['dose_previsto_2025'])
    a = r[r['habilitado_tarde'] == 0].copy()
    a['inse_baixo'] = (a['inse_2019'] < a['inse_2019'].median()).astype(float)
    a['iei_alto'] = (a['iei_medio'] > a['iei_medio'].median()).astype(float)
    print('main sample', len(a), {g: int((a[f'N_{g}_mun_2019'].notna() & a[f'N_{g}_mun_2025'].notna()).sum()) for g in (5, 9)}, flush=True)

    # P2 (items 1, 2 and 4)
    p2, curvas, rob, het = [], [], [], []
    for g in (5, 9):
        dy = f'dN_{g}'
        for d in (a, r):
            d[dy] = d[f'N_{g}_mun_2025'] - d[f'N_{g}_mun_2019']
        rr = ld(a, dy, 'D')
        s = a.dropna(subset=[dy] + W)
        dr = est.resposta_dose(s[dy].values, s['D'].values, s[W].values, s['uf'].values, s['regiao'].values, B=B, seed=2025)
        l = linha(f'beta, {g}th grade', rr)
        l.update(grade=g, beta_p75_dp=l['beta_p75'] * SD_N[g], lo_p75_dp=l['lo_p75'] * SD_N[g], hi_p75_dp=l['hi_p75'] * SD_N[g],
                 att_o=dr['att_o'], att_o_lo=dr['ic_att_o'][0], att_o_hi=dr['ic_att_o'][1], att_o_dp=dr['att_o'] * SD_N[g],
                 acrt=dr['acrt'], acrt_lo=dr['ic_acrt'][0], acrt_hi=dr['ic_acrt'][1], media_2019=s[f'N_{g}_mun_2019'].mean())
        p2.append(l)
        curvas.append(dr['curva'].assign(grade=g))
        rob.append(robustez(a, r, dy, f'N_{g}_mun_2019', f'N {g}th grade'))
        for nome, h in (('Northeast', 'nordeste'), ('INSE 2019 below the median', 'inse_baixo'), ('IEI share above the median', 'iei_alto')):
            a['Dxh'] = a['D'] * a[h]
            q = ld(a, dy, 'D', extra=['Dxh', h]); V = q['V']
            het.append(dict(desfecho=f'N {g}th grade', grupo=nome, beta_fora=q['coef'][0], se_fora=np.sqrt(V[0, 0]),
                            beta_dentro=q['coef'][0] + q['coef'][1], se_dentro=np.sqrt(V[0, 0] + V[1, 1] + 2 * V[0, 1]),
                            diferenca=q['coef'][1], se_diferenca=np.sqrt(V[1, 1]),
                            p_diferenca=p_valor(q['coef'][1], np.sqrt(V[1, 1]), q['clusters']), n=q['n']))
    p2 = pd.DataFrame(p2)
    p2['p_holm'] = holm(p2['p'])
    p2.to_csv(os.path.join(RES, '26_p2.csv'), sep=';', index=False, float_format='%.5f')
    pd.concat(curvas).to_csv(os.path.join(RES, '26_p2_curva.csv'), sep=';', index=False, float_format='%.5f')
    rob = pd.concat(rob); rob.to_csv(os.path.join(RES, '26_p2_robustez.csv'), sep=';', index=False, float_format='%.5f')
    het = pd.DataFrame(het); het.to_csv(os.path.join(RES, '26_p2_heterogeneidade.csv'), sep=';', index=False, float_format='%.5f')
    with pd.option_context('display.width', 250):
        print('--- P2'); print(p2.drop(columns=['especificacao']).round(4).T.to_string())
        print('--- P2 robustness'); print(rob.round(4).to_string(index=False))
        print('--- P2 heterogeneity'); print(het.round(4).to_string(index=False), flush=True)

    # event study, linear trend (items 5 and 6) and coefficients for HonestDiD (script 27)
    ev = []
    for g in (5, 9):
        tab, es = evento(a, f'N_{g}_mun', f'N {g}th grade')
        ev.append(tab)
        pd.DataFrame(es['V'], index=es['anos'], columns=es['anos']).to_csv(os.path.join(RES, f'26_evento_V_{g}.csv'), sep=';', float_format='%.10g')
        ev.append(evento(a, f'N_{g}_mun', f'N {g}th grade, balanced panel', balanceado=True)[0])
    ev = pd.concat(ev)
    ev.to_csv(os.path.join(RES, '26_evento.csv'), sep=';', index=False, float_format='%.6f')
    with pd.option_context('display.width', 250):
        print('--- event study'); print(ev.round(4).to_string(index=False), flush=True)

    # within-municipality comparison and negative control (item 7)
    dentro = []
    for g in (5, 9):
        ok = a[[f'N_{g}_{n}_{y}' for n in ('mun', 'est') for y in (2019, 2025)]].notna().all(axis=1)
        s = a[ok].copy()
        s['dmun'] = s[f'N_{g}_mun_2025'] - s[f'N_{g}_mun_2019']
        s['dest'] = s[f'N_{g}_est_2025'] - s[f'N_{g}_est_2019']
        s['dw'] = s['dmun'] - s['dest']
        for nome, col in (('municipal network, same municipalities', 'dmun'), ('within municipality (municipal minus state)', 'dw'),
                          ('negative control: state network', 'dest')):
            l = linha(f'{nome}, {g}th grade', ld(s, col, 'D'))
            l.update(grade=g, beta_p75_dp=l['beta_p75'] * SD_N[g], lo_p75_dp=l['lo_p75'] * SD_N[g], hi_p75_dp=l['hi_p75'] * SD_N[g])
            dentro.append(l)
    dentro = pd.DataFrame(dentro)
    dentro.to_csv(os.path.join(RES, '26_dentro.csv'), sep=';', index=False, float_format='%.5f')
    with pd.option_context('display.width', 250):
        print('--- within municipality'); print(dentro.round(4).to_string(index=False), flush=True)

    # S1 (item 3)
    s1 = []
    D25, D23 = 'dose_previsto_2025', 'dose_previsto_2023_2025'
    testes = [(f'{v}_{g}_mun', 2019, 2025, D25, g, v) for g in (5, 9) for v in ('ideb', 'mat', 'por', 'P')]
    testes += [(f'N_{g}_mun', 2019, 2023, D23, g, 'N') for g in (5, 9)]
    # the participation tests are not run: item 12 of pap/detalhes_etapa4.md
    testes += [('inse', 2019, 2023, D23, None, 'INSE')]
    for col, y0, y1, dose, g, v in testes:
        a['dy_s1'] = a[f'{col}_{y1}'] - a[f'{col}_{y0}']
        rr = ld(a, 'dy_s1', dose)
        ss = a.dropna(subset=['dy_s1'] + W)
        d2 = est.resposta_dose(ss['dy_s1'].values, ss[dose].values, ss[W].values, ss['uf'].values, ss['regiao'].values, B=B, seed=2025)
        esc = a.loc[a[dose] > 0, dose].quantile(0.75)
        l = linha(f'{v} {g or ""} {y0}-{y1}'.replace('  ', ' '), rr, escala=esc)
        sd = SD_DISC.get((g, v))
        l.update(desfecho=v, grade=g, att_o=d2['att_o'], att_o_lo=d2['ic_att_o'][0], att_o_hi=d2['ic_att_o'][1],
                 beta_p75_dp=l['beta_p75'] / sd if sd else (l['beta_p75'] * SD_N[g] if v == 'N' else np.nan),
                 media_inicial=ss[f'{col}_{y0}'].mean())
        s1.append(l)
    s1 = pd.DataFrame(s1)
    s1['q_bh'] = bh(s1['p'])
    s1.to_csv(os.path.join(RES, '26_s1.csv'), sep=';', index=False, float_format='%.5f')
    with pd.option_context('display.width', 250):
        print('--- S1'); print(s1[['especificacao', 'beta', 'se', 'p', 'q_bh', 'beta_p75', 'beta_p75_dp', 'att_o', 'att_o_lo', 'att_o_hi',
                               'media_inicial', 'n']].round(4).to_string(index=False), flush=True)
