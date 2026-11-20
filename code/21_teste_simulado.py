"""Tests of the estimators in 20_estimacao.py on simulated outcomes. No outcome data are read.

The simulated units are the 5,208 municipal networks of the main sample, with their real dose (2025 prices),
state, immediate region, VAAT position, 2021 transfer and ratio of weighted to enrolled students. Covariates
and outcomes are simulated with known effects. For each estimator the script reports, over repeated draws,
the bias, the RMSE, the coverage of 95% intervals and how often the test rejects (under the null, under the
alternative and under violations of the assumptions).
  ld      long difference (PAP Section 7.1): clustered and HC1 errors, with and without an effect
  dose    dose response (7.2): concave h; ATT^o, mean h', ATT(d) at the median and p90 of the positive dose
  es      event study (7.3) and linear-trend correction (7.5, item 2): no pre-trend, a dose-specific linear
          pre-trend, and an unbalanced panel
  dentro  within-municipality comparison and negative control (7.4), with and without local confounding
  honest  HonestDiD relative-magnitudes bounds (7.5, item 1)                      [needs R and HonestDiD]
  kink    fuzzy kink, placebo thresholds, permutation and density tests (7.6)  [needs rdrobust, rddensity]
Usage: python 21_teste_simulado.py <part> [<part> ...] [--reps N] [--bloco K]
  kink and honest run in blocks (each block a separate process with its own seed) and write
  results/21_simulacao_<part>_<K>.csv; the parts resumo_kink and resumo_honest then pool the blocks.
Output: results/21_simulacao_<part>.csv
The files in the repository come from: ld, dose, es and dentro with the default number of draws (cloud
container, 2 cores); kink blocks 0 and 1 with --reps 12 and blocks 2 and 3 with --reps 55; honest blocks 0 to 5
and 7 with --reps 2 (block 6 was interrupted by a time limit and left out). Each HonestDiD draw takes about
a minute.
"""
import os, sys, json, time, argparse, importlib.util
import numpy as np
import pandas as pd
from scipy import stats
from config import DADOS, RES

AQUI = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('est', os.path.join(AQUI, '20_estimacao.py'))
est = importlib.util.module_from_spec(spec); spec.loader.exec_module(est)

ANOS = list(range(2005, 2026, 2))
GAMMA = np.array([0.05, -0.03, 0.02])


def mundo(seed=0):
    """Fixed part of the simulated world: the real treatment data plus simulated covariates (correlated with
    the VAAT position), state effects correlated with the state's mean dose, and unit error scales that fall
    with network size."""
    b = pd.read_csv(os.path.join(RES, '13_vaat_redes.csv'), sep=';')
    b = b[b['habilitado_tarde'] == 0].reset_index(drop=True)
    reg = {m['id']: m['regiao-imediata']['id'] for m in json.load(open(os.path.join(DADOS, 'ibge_municipios.json')))}
    b['regiao'] = b['ibge'].map(reg)
    assert b['regiao'].notna().all() and len(b) == 5208
    b['dose'] = b['dose_previsto_2025']
    b['razao'] = b['mat_vaat'] / b['mat_censo']
    rng = np.random.default_rng(seed)
    z = ((b['x'] - b['x'].mean()) / b['x'].std()).values
    n = len(b)
    b['z'] = z
    for c, a in (('w1', 0.5), ('w2', -0.3), ('w3', 0.4)):
        b[c] = a * z + rng.normal(size=n)
    ufs = b['uf'].unique()
    efeito_uf = dict(zip(ufs, rng.normal(0, 0.05, len(ufs))))
    b['lam'] = 0.02 * b.groupby('uf')['dose'].transform('mean') + b['uf'].map(efeito_uf)
    b['sig'] = 0.3 * np.clip((b['mat_censo'] / b['mat_censo'].median()) ** -0.25, 0.5, 2.0)
    b['reg_i'] = pd.factorize(b['regiao'])[0]
    return b


def erro(b, rng, sd_reg=0.1):
    return rng.normal(0, sd_reg, b['reg_i'].max() + 1)[b['reg_i'].values] + rng.normal(size=len(b)) * b['sig'].values


def resumo(teste, verdade, e, se=None, G=None, lo=None, hi=None, **extra):
    e = np.asarray(e, dtype=float)
    d = dict(teste=teste, verdade=verdade, media=e.mean(), vies=e.mean() - verdade, dp=e.std(ddof=1),
             rmse=np.sqrt(np.mean((e - verdade) ** 2)), reps=len(e))
    if se is not None:
        se = np.asarray(se, dtype=float)
        t = stats.t.ppf(0.975, G - 1) if G else 1.96
        d.update(se_medio=se.mean(), cobertura=np.mean(np.abs(e - verdade) <= t * se), rejeita_zero=np.mean(np.abs(e) > t * se))
    if lo is not None:
        lo, hi = np.asarray(lo, dtype=float), np.asarray(hi, dtype=float)
        d.update(cobertura=np.mean((lo <= verdade) & (verdade <= hi)), rejeita_zero=np.mean((lo > 0) | (hi < 0)))
    d.update(extra)
    return d


def parte_ld(b, R, seed=11):
    rng = np.random.default_rng(seed)
    W, D = b[['w1', 'w2', 'w3']].values, b['dose'].values
    linhas = []
    for beta in (0.02, 0.0):
        cl, hc = [], []
        for _ in range(R):
            dy = b['lam'].values + beta * D + W @ GAMMA + erro(b, rng)
            cl.append(est.diferenca_longa(dy, D, W, b['uf'].values, cluster=b['regiao'].values))
            hc.append(est.diferenca_longa(dy, D, W, b['uf'].values))
        G = cl[0]['clusters']
        linhas.append(resumo(f'ld_beta{beta}_cluster', beta, [r['beta'] for r in cl], [r['se'] for r in cl], G))
        linhas.append(resumo(f'ld_beta{beta}_hc1', beta, [r['beta'] for r in hc], [r['se'] for r in hc]))
    return linhas


def parte_dose(b, R, B=199, seed=12):
    rng = np.random.default_rng(seed)
    h = lambda d: 0.12 * (1 - np.exp(-d / 4))
    dh = lambda d: 0.03 * np.exp(-d / 4)
    W, D = b[['w1', 'w2', 'w3']].values, b['dose'].values
    pos = D > 0
    grade = np.quantile(D[pos], [0.5, 0.9])
    alvo = dict(att_o=h(D[pos]).mean(), acrt=dh(D[pos]).mean(), att_p50=h(grade[0]), att_p90=h(grade[1]))
    out = {k: [] for k in alvo}; ld = []
    for r_ in range(R):
        dy = b['lam'].values + pos * h(D) + W @ GAMMA + erro(b, rng)
        r = est.resposta_dose(dy, D, W, b['uf'].values, b['regiao'].values, B=B, seed=1000 + r_, grade=grade)
        out['att_o'].append((r['att_o'], r['se_att_o'], *r['ic_att_o']))
        out['acrt'].append((r['acrt'], r['se_acrt'], *r['ic_acrt']))
        for k, i in (('att_p50', 0), ('att_p90', 1)):
            c = r['curva'].iloc[i]
            out[k].append((c['att'], c['se'], c['lo'], c['hi']))
        ld.append(est.diferenca_longa(dy, D, W, b['uf'].values, cluster=b['regiao'].values)['beta'])
    linhas = []
    for k, v in out.items():
        v = np.array(v)
        linhas.append(resumo(f'dose_{k}_percentil', alvo[k], v[:, 0], lo=v[:, 2], hi=v[:, 3], B=B))
        linhas.append(resumo(f'dose_{k}_normal', alvo[k], v[:, 0], se=v[:, 1], B=B))
    linhas.append(resumo('dose_ld_beta_vs_media_hlinha', alvo['acrt'], ld,
                         nota='long-difference beta when h is concave; compared with the mean of h prime'))
    return linhas


def painel(b):
    p = b[['ibge', 'uf', 'regiao', 'reg_i', 'dose', 'w1', 'sig']].loc[b.index.repeat(len(ANOS))].reset_index(drop=True)
    p['ano'] = np.tile(ANOS, len(b))
    return p.rename(columns={'ibge': 'id', 'regiao': 'cluster'})


def simula_painel(p, rng, betas, rho=0.6):
    n, T = len(p) // len(ANOS), len(ANOS)
    sig = p['sig'].values.reshape(n, T)[:, 0]
    e = np.empty((n, T)); e[:, 0] = rng.normal(size=n) * sig
    for t in range(1, T):
        e[:, t] = rho * e[:, t - 1] + np.sqrt(1 - rho ** 2) * rng.normal(size=n) * sig
    G = p['reg_i'].max() + 1
    v = rng.normal(0, 0.1, (G, T))[p['reg_i'].values.reshape(n, T)[:, 0]]
    ufs = pd.factorize(p['uf'])[0].reshape(n, T)[:, 0]
    lam = rng.normal(0, 0.2, (ufs.max() + 1, T))[ufs]
    alfa = rng.normal(0, 0.5, n)[:, None]
    k = (np.array(ANOS) - 2019) / 2
    bt = np.array([betas.get(a, 0.0) for a in ANOS])
    y = alfa + lam + p['dose'].values.reshape(n, T) * bt + p['w1'].values.reshape(n, T) * 0.01 * k + v + e
    return y.ravel()


def parte_es(b, R, seed=13, wild_reps=500):
    rng = np.random.default_rng(seed)
    p = painel(b)
    efeito = {2021: 0.005, 2023: 0.015, 2025: 0.02}
    delta = 0.002
    cenarios = {'sem_pretendencia': efeito,
                'pretendencia_linear': {a: efeito.get(a, 0) + delta * (a - 2019) / 2 for a in ANOS},
                'desbalanceado': efeito}
    linhas = []
    for nome, bt in cenarios.items():
        reps = R if nome != 'desbalanceado' else max(R // 3, 30)
        res, lin = [], []
        for r_ in range(reps):
            q = p.assign(y=simula_painel(p, rng, bt))
            if nome == 'desbalanceado':
                q = q[rng.random(len(q)) > 0.10]
            es = est.estudo_evento(q, 'y', 'dose', ['w1'], wild_B=199 if r_ < wild_reps else 0, seed=r_)
            res.append(es)
            if nome == 'pretendencia_linear':
                lin.append(est.tendencia_linear(es))
        G = res[0]['clusters']
        for a in (2005, 2017, 2023, 2025):
            v = np.array([r['tabela'].set_index('ano').loc[a, ['beta', 'se']].values for r in res])
            linhas.append(resumo(f'es_{nome}_beta{a}', bt.get(a, 0.0), v[:, 0], v[:, 1], G))
        linhas.append(dict(teste=f'es_{nome}_teste_pre', rejeita_zero=np.mean([r['p_pre'] < 0.05 for r in res]),
                           media=np.mean([r['F_pre'] for r in res]), reps=reps,
                           nota='joint F test of beta_k = 0 for k <= 2017, CR1 with F(q, G-1)'))
        pw = [r['p_pre_wild'] for r in res if np.isfinite(r['p_pre_wild'])]
        if pw:
            linhas.append(dict(teste=f'es_{nome}_teste_pre_wild', rejeita_zero=np.mean(np.array(pw) < 0.05), reps=len(pw),
                               nota='same test, restricted wild cluster bootstrap p-value (B = 199)'))
        if lin:
            linhas.append(resumo(f'es_{nome}_beta2025_menos_tendencia', efeito[2025],
                                 [l['beta_ajustado'] for l in lin], [l['se'] for l in lin], G))
    return linhas


def parte_dentro(b, R, seed=14):
    rng = np.random.default_rng(seed)
    prob = np.log(b['mat_censo'].values); prob = prob / prob.sum()
    s = b.iloc[np.sort(rng.choice(len(b), 1000, replace=False, p=prob))].reset_index(drop=True)
    W, D, uf, cl = s[['w1', 'w2', 'w3']].values, s['dose'].values, s['uf'].values, s['regiao'].values
    mu = s['uf'].map(dict(zip(s['uf'].unique(), rng.normal(0, 0.05, s['uf'].nunique())))).values
    beta = 0.02
    linhas = []
    for kappa in (0.0, 0.03):
        r = {k: [] for k in ('ingenuo', 'dentro', 'controle_negativo')}
        for _ in range(R):
            c = -kappa * s['z'].values + rng.normal(0, 0.1, len(s))
            dm = s['lam'].values + beta * D + W @ GAMMA + c + erro(s, rng)
            de = mu + W @ (GAMMA / 2) + c + erro(s, rng)
            r['ingenuo'].append(est.diferenca_longa(dm, D, W, uf, cluster=cl))
            r['dentro'].append(est.diferenca_longa(dm - de, D, W, uf, cluster=cl))
            r['controle_negativo'].append(est.diferenca_longa(de, D, W, uf, cluster=cl))
        for k, v in r.items():
            linhas.append(resumo(f'dentro_kappa{kappa}_{k}', 0.0 if k == 'controle_negativo' else beta,
                                 [x['beta'] for x in v], [x['se'] for x in v], v[0]['clusters'],
                                 municipios=len(s), dose_positiva=int((D > 0).sum())))
    return linhas


HONEST = (('efeito0.02', {2021: 0.005, 2023: 0.015, 2025: 0.02}),
          ('efeito0.01', {2021: 0.0025, 2023: 0.0075, 2025: 0.01}),
          ('efeito0.02_pretendencia', {a: {2021: 0.005, 2023: 0.015, 2025: 0.02}.get(a, 0) + 0.002 * (a - 2019) / 2 for a in ANOS}))


def parte_honest(b, R, seed=15, bloco=0, rscript=None):
    """One scenario per block (block mod 3): an effect of 0.02 in 2025 (about 6 standard errors), of 0.01
    (about 3), and 0.02 plus a dose-specific linear pre-trend. Interval at Mbar = 1 and the breakdown Mbar."""
    rng = np.random.default_rng(seed + 100 * bloco)
    nome, bt = HONEST[bloco % 3]
    p = painel(b)
    linhas = []
    for _ in range(R):
        es = est.estudo_evento(p.assign(y=simula_painel(p, rng, bt)), 'y', 'dose', ['w1'], wild_B=0)
        t0 = time.time()
        h = est.honestdid_rm(es, mbar=(1.0,), rscript=rscript, tol=0.1)
        tb = es['tabela'].set_index('ano')
        pre = np.r_[tb.loc[[a for a in ANOS if a < 2019], 'beta'].values, 0.0]
        linhas.append(dict(cenario=nome, verdade=bt[2025] - (0.006 if 'pretendencia' in nome else 0), beta=tb.loc[2025, 'beta'],
                           se=tb.loc[2025, 'se'],
                           lo_original=h['ic_original'][0], hi_original=h['ic_original'][1],
                           lo_m1=h['limites']['lb'].iloc[0], hi_m1=h['limites']['ub'].iloc[0], quebra=h['quebra'],
                           maior_variacao_pre=np.abs(np.diff(pre)).max(), segundos=time.time() - t0))
    return linhas


def resumo_honest():
    arq = [f for f in os.listdir(RES) if f.startswith('21_simulacao_honest_') and f.endswith('.csv')]
    k = pd.concat([pd.read_csv(os.path.join(RES, f), sep=';') for f in arq], ignore_index=True)
    linhas = []
    for nome, g in k.groupby('cenario'):
        v = {n: bt[2025] for n, bt in HONEST}[nome] - (0.006 if 'pretendencia' in nome else 0)   # effect net of the trend
        linhas.append(dict(cenario=nome, verdade=v, reps=len(g), t_medio=(g['beta'] / g['se']).mean(),
                           cobre_original=np.mean((g['lo_original'] <= v) & (v <= g['hi_original'])),
                           cobre_m1=np.mean((g['lo_m1'] <= v) & (v <= g['hi_m1'])),
                           m1_inclui_zero=np.mean((g['lo_m1'] <= 0) & (g['hi_m1'] >= 0)),
                           quebra_mediana=g['quebra'].median(), quebra_min=g['quebra'].min(), quebra_max=g['quebra'].max(),
                           quebra_abaixo_1=np.mean(g['quebra'] < 1), variacao_pre_mediana=g['maior_variacao_pre'].median(),
                           segundos=g['segundos'].mean()))
    t = pd.DataFrame(linhas)
    t.to_csv(os.path.join(RES, '21_simulacao_honest.csv'), sep=';', index=False, float_format='%.5f')
    return t


def parte_kink(b, R, seed=16, bloco=0):
    """First stage: the 2021 complementation per enrolled student (thousand reais), from the real transfers.
    Outcome: change in spending per enrolled student, a smooth quadratic in x plus tau times the first stage,
    plus normal errors. Their SD, 1.26 thousand, is the dispersion that the power calculation of the plan
    (Section 9, h = 0.2) implies, rescaled to the first-stage slope used here."""
    rng = np.random.default_rng(seed + 100 * bloco)
    x = b['x'].values
    fs = b['recebido_2021'].values * b['razao'].values / 1000
    suave = 0.5 + 1.0 * x - 0.8 * x ** 2
    linhas = []
    for tau in (0.0, 0.82, 1.0):
        for _ in range(R):
            y = suave + tau * fs + rng.normal(0, 1.26, len(x))
            k = est.kink(y, x, fs)
            l = dict(parte='fuzzy', tau=tau, est=k['repasse'], lo=k['ic_repasse'][0], hi=k['ic_repasse'][1], h=k['h'],
                     lo_conv=k['ic_repasse_convencional'][0], hi_conv=k['ic_repasse_convencional'][1], kink_fs=k['kink_fs'])
            for hh in (0.1, 0.2):
                kh = est.kink(y, x, fs, h=hh)
                s = f'_h{hh}'
                l.update({'est' + s: kh['repasse'], 'lo' + s: kh['ic_repasse'][0], 'hi' + s: kh['ic_repasse'][1],
                          'lo_conv' + s: kh['ic_repasse_convencional'][0], 'hi_conv' + s: kh['ic_repasse_convencional'][1]})
            linhas.append(l)
            if tau != 0.82:
                pl = est.kink_placebo(y, x)
                pm = est.permutacao_kink(y, x, n_placebo=200, seed=int(rng.integers(1e9)))
                linhas.append(dict(parte='placebo', tau=tau, rejeita=int((pl['p'] < 0.05).sum()), limiares=len(pl),
                                   p_perm=pm['p']))
    for manip in (0.0, 0.3):
        for _ in range(R):
            xs = rng.normal(0.15, 0.25, len(x))
            m = (xs > 0) & (xs < 0.05) & (rng.random(len(x)) < manip)
            xs[m] -= 0.05
            linhas.append(dict(parte='densidade', tau=manip, p_dens=est.densidade(xs)))
    return linhas


def resumo_kink():
    arq = [f for f in os.listdir(RES) if f.startswith('21_simulacao_kink_') and f.endswith('.csv')]
    k = pd.concat([pd.read_csv(os.path.join(RES, f), sep=';') for f in arq], ignore_index=True)
    linhas = []
    f = k[k['parte'] == 'fuzzy']
    for tau, g in f.groupby('tau'):
        for s, nome in (('', 'h_mse'), ('_h0.1', 'h0.1'), ('_h0.2', 'h0.2')):
            razao = ((g['hi' + s] - g['lo' + s]) / (g['hi_conv' + s] - g['lo_conv' + s])).median()
            linhas.append(resumo(f'kink_fuzzy_tau{tau}_{nome}_robusto', tau, g['est' + s], lo=g['lo' + s], hi=g['hi' + s],
                                 mediana=g['est' + s].median(), largura_mediana=(g['hi' + s] - g['lo' + s]).median(),
                                 razao_robusto_convencional=razao, h_medio=g['h'].mean() if s == '' else float(s[2:])))
            linhas.append(resumo(f'kink_fuzzy_tau{tau}_{nome}_convencional', tau, g['est' + s], lo=g['lo_conv' + s],
                                 hi=g['hi_conv' + s], largura_mediana=(g['hi_conv' + s] - g['lo_conv' + s]).median()))
    for tau, g in k[k['parte'] == 'placebo'].groupby('tau'):
        linhas.append(dict(teste=f'kink_placebo_limiares_tau{tau}', rejeita_zero=g['rejeita'].sum() / g['limiares'].sum(), reps=len(g)))
        linhas.append(dict(teste=f'kink_permutacao_tau{tau}', rejeita_zero=np.mean(g['p_perm'] < 0.05), reps=len(g)))
    for m, g in k[k['parte'] == 'densidade'].groupby('tau'):
        linhas.append(dict(teste=f'densidade_manipulacao{m}', rejeita_zero=np.mean(g['p_dens'] < 0.05), reps=len(g)))
    pd.DataFrame(linhas).to_csv(os.path.join(RES, '21_simulacao_kink.csv'), sep=';', index=False, float_format='%.5f')
    return pd.DataFrame(linhas)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('partes', nargs='+')
    ap.add_argument('--reps', type=int, default=None)
    ap.add_argument('--bloco', type=int, default=0)
    a = ap.parse_args()
    b = mundo()
    padrao = dict(ld=1000, dose=200, es=1000, dentro=500, kink=10, honest=2)
    for parte in a.partes:
        t0 = time.time()
        R = a.reps or padrao.get(parte)
        if parte in ('kink', 'honest'):
            out = pd.DataFrame(parte_kink(b, R, bloco=a.bloco) if parte == 'kink' else
                               parte_honest(b, R, bloco=a.bloco, rscript=os.environ.get('RSCRIPT')))
            out.to_csv(os.path.join(RES, f'21_simulacao_{parte}_{a.bloco}.csv'), sep=';', index=False, float_format='%.6f')
            print(parte, a.bloco, len(out), f'{time.time() - t0:.0f}s', flush=True)
            continue
        if parte in ('resumo_kink', 'resumo_honest'):
            print((resumo_kink() if parte == 'resumo_kink' else resumo_honest()).round(4).to_string(index=False)); continue
        f = dict(ld=parte_ld, dose=parte_dose, es=parte_es, dentro=parte_dentro)
        out = f[parte](b, R)
        out.to_csv(os.path.join(RES, f'21_simulacao_{parte}.csv'), sep=';', index=False, float_format='%.5f')
        print(f'--- {parte} ({time.time() - t0:.0f}s)')
        print(out.round(4).to_string(index=False), flush=True)
