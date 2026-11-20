"""Estimators of the VAAT pre-analysis plan (doi:10.5281/zenodo.24391651). This module reads no data.

  diferenca_longa  long difference with a continuous dose and state fixed effects (Section 7.1)
  resposta_dose    nonparametric dose response after Callaway, Goodman-Bacon and Sant'Anna (Section 7.2)
  estudo_evento    event study with unit and state-by-year fixed effects (Section 7.3); pre-trend test with a
                   wild cluster bootstrap p-value (Addendum 1)
  tendencia_linear dose-specific linear pre-trend, extrapolated (Section 7.5, item 2)
  honestdid_rm     relative-magnitudes bounds of Rambachan and Roth, through R's HonestDiD (Section 7.5)
  kink             fuzzy regression kink with rdrobust, density test and placebo checks (Section 7.6)
Standard errors are clustered (CR1) by the variable given as cluster; with cluster=None they are HC1.
"""
import os, subprocess, tempfile
import numpy as np
import pandas as pd
from scipy import stats
from scipy.interpolate import BSpline


def _arr(v):
    return np.asarray(v, dtype=float)


def desvio_grupo(M, grupo, w=None):
    """Subtract the (weighted) group mean from each column of M."""
    M = np.atleast_2d(_arr(M).T).T
    w = np.ones(len(M)) if w is None else _arr(w)
    g = pd.factorize(pd.Series(grupo))[0]
    soma_w = np.bincount(g, weights=w)
    out = np.empty_like(M)
    for j in range(M.shape[1]):
        out[:, j] = M[:, j] - (np.bincount(g, weights=w * M[:, j]) / soma_w)[g]
    return out


def mqo(y, X, cluster=None, w=None, k_extra=0):
    """(Weighted) least squares without an added constant. Returns coefficients, covariance and SE.
    k_extra counts absorbed parameters that are not nested in the clusters (small-sample correction)."""
    y, X = _arr(y), np.atleast_2d(_arr(X).T).T
    w = np.ones(len(y)) if w is None else _arr(w)
    sw = np.sqrt(w)
    Xw, yw = X * sw[:, None], y * sw
    XtX_inv = np.linalg.pinv(Xw.T @ Xw)
    b = XtX_inv @ Xw.T @ yw
    u = yw - Xw @ b
    n, k = X.shape
    kk = k + k_extra
    if cluster is None:
        meat = (Xw * u[:, None]).T @ (Xw * u[:, None])
        V = XtX_inv @ meat @ XtX_inv * n / (n - kk)
        G = n
    else:
        g = pd.factorize(pd.Series(cluster))[0]
        G = g.max() + 1
        S = np.zeros((G, k))
        np.add.at(S, g, Xw * u[:, None])
        V = XtX_inv @ (S.T @ S) @ XtX_inv * G / (G - 1) * (n - 1) / (n - kk)
    return dict(b=b, V=V, se=np.sqrt(np.diag(V)), n=n, G=G)


def diferenca_longa(dy, dose, W, uf, cluster=None, w=None):
    """Delta Y = lambda_uf + beta * dose + gamma'W + e. Returns beta, its SE, n and number of clusters."""
    ok = np.isfinite(_arr(dy)) & np.isfinite(_arr(dose))
    W = np.zeros((len(ok), 0)) if W is None else np.atleast_2d(_arr(W).T).T
    ok &= np.isfinite(W).all(axis=1)
    sel = lambda v: None if v is None else np.asarray(v)[ok]
    X = np.column_stack([_arr(dose)[ok], W[ok]])
    wy = sel(w)
    Xd = desvio_grupo(X, sel(uf), wy)
    yd = desvio_grupo(_arr(dy)[ok], sel(uf), wy)[:, 0]
    r = mqo(yd, Xd, cluster=sel(cluster), w=wy, k_extra=len(np.unique(sel(uf))))
    return dict(beta=r['b'][0], se=r['se'][0], n=r['n'], clusters=r['G'], coef=r['b'], V=r['V'])


def _base(x, nos, grau=3, deriv=0):
    t = np.r_[[nos[0]] * (grau + 1), nos[1:-1], [nos[-1]] * (grau + 1)]
    x = np.clip(_arr(x), nos[0], nos[-1])
    if deriv == 0:
        return BSpline.design_matrix(x, t, grau).toarray()
    k = len(t) - grau - 1
    return np.column_stack([BSpline(t, np.eye(k)[j], grau).derivative(deriv)(x) for j in range(k)])


def resposta_dose(dy, dose, W, uf, cluster, B=999, seed=1, grade=None):
    """Delta Y = lambda_uf + gamma'W + 1[D>0] h(D) + e, with h a cubic B-spline (interior knots at the terciles
    of the positive dose). Zero-dose units are the comparison group. Returns ATT(d) on a grid, ATT^o (mean of
    h over the treated), the mean of h' over the treated, and cluster-bootstrap SEs and percentile intervals."""
    dy, dose = _arr(dy), _arr(dose)
    W = np.zeros((len(dy), 0)) if W is None else np.atleast_2d(_arr(W).T).T
    ok = np.isfinite(dy) & np.isfinite(dose) & np.isfinite(W).all(axis=1)
    dy, dose, W = dy[ok], dose[ok], W[ok]
    uf, cluster = np.asarray(uf)[ok], np.asarray(cluster)[ok]
    pos = dose > 0
    nos = np.r_[dose[pos].min(), np.quantile(dose[pos], [1 / 3, 2 / 3]), dose[pos].max()]
    grade = np.linspace(nos[0], nos[-1], 25) if grade is None else _arr(grade)
    B0 = np.zeros((len(dy), len(nos) + 2)); B0[pos] = _base(dose[pos], nos)
    B1 = np.zeros_like(B0); B1[pos] = _base(dose[pos], nos, deriv=1)
    Bg = _base(grade, nos)
    XW = np.column_stack([W, B0])

    def ajusta(idx):
        p = pos[idx]
        Xd = desvio_grupo(XW[idx], uf[idx])
        yd = desvio_grupo(dy[idx], uf[idx])[:, 0]
        b = np.linalg.lstsq(Xd, yd, rcond=None)[0]
        gam = b[W.shape[1]:]
        return np.r_[(B0[idx][p] @ gam).mean(), (B1[idx][p] @ gam).mean(), Bg @ gam]

    est = ajusta(np.arange(len(dy)))
    rng = np.random.default_rng(seed)
    cl = pd.factorize(pd.Series(cluster))[0]
    membros = [np.flatnonzero(cl == c) for c in range(cl.max() + 1)]
    boot = np.array([ajusta(np.concatenate([membros[c] for c in rng.integers(0, len(membros), len(membros))]))
                     for _ in range(B)])
    se = boot.std(axis=0, ddof=1)
    lo, hi = np.quantile(boot, [0.025, 0.975], axis=0)
    return dict(att_o=est[0], se_att_o=se[0], ic_att_o=(lo[0], hi[0]),
                acrt=est[1], se_acrt=se[1], ic_acrt=(lo[1], hi[1]),
                curva=pd.DataFrame({'dose': grade, 'att': est[2:], 'se': se[2:], 'lo': lo[2:], 'hi': hi[2:]}),
                n=len(dy), tratados=int(pos.sum()), nos=nos)


def _absorve_duas(M, a, b, tol=1e-10, max_iter=1000):
    """Remove two sets of fixed effects (a, b) from each column of M by alternating projections."""
    M = np.atleast_2d(_arr(M).T).T.copy()
    ga, gb = pd.factorize(pd.Series(a))[0], pd.factorize(pd.Series(b))[0]
    na, nb = np.bincount(ga), np.bincount(gb)
    for j in range(M.shape[1]):
        v = M[:, j]
        for _ in range(max_iter):
            v0 = v
            v = v - (np.bincount(ga, weights=v) / na)[ga]
            v = v - (np.bincount(gb, weights=v) / nb)[gb]
            if np.max(np.abs(v - v0)) < tol:
                break
        M[:, j] = v
    return M


def wild_wald(y, X, cluster, teste, B=999, seed=1):
    """p-value of the cluster-robust Wald test of b[teste] = 0 by the restricted wild cluster bootstrap
    (Rademacher weights; Cameron, Gelbach and Miller 2008). y and X already have the fixed effects removed."""
    g = pd.factorize(pd.Series(cluster))[0]
    G = g.max() + 1
    XtX_inv = np.linalg.pinv(X.T @ X)
    Q = X @ XtX_inv[teste].T                                  # b[teste] = Q'y

    def wald(u_cols):                                         # u_cols: residuals, b: Q'y
        S = np.column_stack([np.bincount(g, weights=Q[:, j] * u_cols, minlength=G) for j in range(Q.shape[1])])
        return S.T @ S
    b = Q.T @ y
    u = y - X @ (XtX_inv @ (X.T @ y))
    W0 = float(b @ np.linalg.solve(wald(u), b))
    livre = np.setdiff1d(np.arange(X.shape[1]), teste)
    XR = X[:, livre]
    uR = y - XR @ np.linalg.lstsq(XR, y, rcond=None)[0]
    rng = np.random.default_rng(seed)
    Wb = np.empty(B)
    for j in range(B):
        e = uR * rng.choice([-1.0, 1.0], G)[g]               # restricted fit lies in span(X): drops out of b* and u*
        bb = Q.T @ e
        ub = e - X @ (XtX_inv @ (X.T @ e))
        Wb[j] = bb @ np.linalg.solve(wald(ub), bb)
    return float((1 + np.sum(Wb >= W0)) / (B + 1))


def estudo_evento(p, y, dose, controles, ano_ref=2019, cluster='cluster', anos_pre_teste=None, wild_B=999, seed=1):
    """Y_it = alpha_i + lambda_(uf,t) + sum_k beta_k D_i 1[t=k] + sum_k gamma_k'W_i 1[t=k] + e_it.
    p: one row per unit and year with columns id, ano, uf, the cluster, y, dose and the controls.
    Returns the beta_k with SE and covariance, and a joint F test of beta_k = 0 for the years in
    anos_pre_teste (default: every year before ano_ref), with two p-values: from F(q, G-1) with the CR1 covariance
    (p_pre) and from the restricted wild cluster bootstrap with wild_B draws (p_pre_wild; skipped if wild_B = 0).
    Addendum 1 to the plan makes p_pre_wild the main p-value, because p_pre over-rejects in script 21."""
    p = p.dropna(subset=[y, dose] + list(controles)).copy()
    anos = sorted(p['ano'].unique())
    outros = [a for a in anos if a != ano_ref]
    cols = []
    for a in outros:
        p[f'_d{a}'] = p[dose] * (p['ano'] == a)
        cols.append(f'_d{a}')
    for c in controles:
        for a in outros:
            p[f'_{c}{a}'] = p[c] * (p['ano'] == a)
            cols.append(f'_{c}{a}')
    uf_ano = p['uf'].astype(str) + '_' + p['ano'].astype(str)
    Z = _absorve_duas(p[[y] + cols].values, p['id'].values, uf_ano.values)
    r = mqo(Z[:, 0], Z[:, 1:], cluster=p[cluster].values, k_extra=uf_ano.nunique())
    k = len(outros)
    b, V = r['b'][:k], r['V'][:k, :k]
    tab = pd.DataFrame({'ano': outros, 'beta': b, 'se': np.sqrt(np.diag(V))})
    pre = [a for a in (anos_pre_teste if anos_pre_teste is not None else [a for a in outros if a < ano_ref])]
    i = [outros.index(a) for a in pre]
    bp, Vp = b[i], V[np.ix_(i, i)]
    F = float(bp @ np.linalg.solve(Vp, bp)) / len(i)
    pval = 1 - stats.f.cdf(F, len(i), r['G'] - 1)
    pw = wild_wald(Z[:, 0], Z[:, 1:], p[cluster].values, i, B=wild_B, seed=seed) if wild_B else np.nan
    return dict(tabela=tab, V=V, anos=outros, F_pre=F, p_pre=pval, p_pre_wild=pw, n=r['n'], clusters=r['G'],
                unidades=p['id'].nunique())


def tendencia_linear(es, anos_ajuste=(2009, 2011, 2013, 2015, 2017), alvo=2025, ano_ref=2019):
    """Fit beta_k = a + c (k - ano_ref) on the pre-period coefficients and subtract the extrapolation from
    beta_alvo. SE by the delta method with the event-study covariance."""
    anos = es['anos']
    i = [anos.index(a) for a in anos_ajuste]
    j = anos.index(alvo)
    X = np.column_stack([np.ones(len(i)), np.array(anos_ajuste) - ano_ref])
    A = np.linalg.solve(X.T @ X, X.T)                      # (a, c) = A beta_pre
    L = np.zeros(len(anos)); L[j] = 1.0
    L[i] -= np.array([1.0, alvo - ano_ref]) @ A
    b = es['tabela']['beta'].values
    return dict(beta_ajustado=float(L @ b), se=float(np.sqrt(L @ es['V'] @ L)))


def honestdid_rm(es, alvo=2025, ano_ref=2019, mbar=(0.5, 1.0, 1.5, 2.0), rscript=None, tol=0.05, teto=16.0):
    """Relative-magnitudes bounds (Rambachan and Roth 2023) for beta_alvo, with R's HonestDiD. Pre-period
    coefficients are those before ano_ref; post-period coefficients those after it. Returns the 95% interval for
    each Mbar, the original interval, and the breakdown Mbar: the smallest Mbar whose interval contains zero,
    found by bisection to within tol (0 if the original interval contains zero; inf if none up to teto)."""
    anos = es['anos']
    ordem = [a for a in anos if a < ano_ref] + [a for a in anos if a > ano_ref]
    idx = [anos.index(a) for a in ordem]
    b = es['tabela']['beta'].values[idx]
    V = es['V'][np.ix_(idx, idx)]
    npre = sum(a < ano_ref for a in ordem); npos = len(ordem) - npre
    l = np.zeros(npos); l[[a for a in ordem if a > ano_ref].index(alvo)] = 1
    rscript = rscript or os.environ.get('RSCRIPT', 'Rscript')
    with tempfile.TemporaryDirectory() as tmp:
        np.savetxt(os.path.join(tmp, 'b.csv'), b, delimiter=',')
        np.savetxt(os.path.join(tmp, 'V.csv'), V, delimiter=',')
        np.savetxt(os.path.join(tmp, 'l.csv'), l, delimiter=',')
        np.savetxt(os.path.join(tmp, 'm.csv'), np.sort(np.r_[list(mbar)]), delimiter=',')
        codigo = f"""
suppressPackageStartupMessages(library(HonestDiD))
d <- '{tmp}'
b <- as.numeric(read.csv(file.path(d,'b.csv'), header=FALSE)[,1])
V <- as.matrix(read.csv(file.path(d,'V.csv'), header=FALSE))
l <- as.numeric(read.csv(file.path(d,'l.csv'), header=FALSE)[,1])
m <- as.numeric(read.csv(file.path(d,'m.csv'), header=FALSE)[,1])
ic <- function(x) {{ r <- createSensitivityResults_relativeMagnitudes(betahat=b, sigma=V, numPrePeriods={npre},
                       numPostPeriods={npos}, l_vec=l, Mbarvec=x); c(r$lb, r$ub) }}
zero <- function(v) v[1] <= 0 && v[2] >= 0
o <- constructOriginalCS(betahat=b, sigma=V, numPrePeriods={npre}, numPostPeriods={npos}, l_vec=l)
res <- t(sapply(m, ic))
quebra <- NA
if (zero(c(o$lb, o$ub))) quebra <- 0 else {{
  k <- which(apply(res, 1, zero)); lo <- 0; hi <- NA
  if (length(k)) {{ hi <- m[min(k)]; if (min(k) > 1) lo <- m[min(k) - 1] }} else {{
    lo <- max(m); x <- 2 * max(m)
    while (x <= {teto}) {{ if (zero(ic(x))) {{ hi <- x; break }}; lo <- x; x <- 2 * x }}
  }}
  if (is.na(hi)) quebra <- Inf else {{
    while (hi - lo > {tol}) {{ mid <- (lo + hi) / 2; if (zero(ic(mid))) hi <- mid else lo <- mid }}
    quebra <- hi
  }}
}}
write.csv(rbind(data.frame(lb=res[,1], ub=res[,2], Mbar=m), data.frame(lb=o$lb, ub=o$ub, Mbar=-1),
                data.frame(lb=quebra, ub=quebra, Mbar=-2)), file.path(d,'out.csv'), row.names=FALSE)
"""
        open(os.path.join(tmp, 'h.R'), 'w').write(codigo)
        subprocess.run([rscript, os.path.join(tmp, 'h.R')], check=True, capture_output=True, text=True)
        out = pd.read_csv(os.path.join(tmp, 'out.csv'))
    orig = out[out['Mbar'] == -1].iloc[0]
    return dict(limites=out[out['Mbar'] >= 0].reset_index(drop=True), quebra=float(out.loc[out['Mbar'] == -2, 'lb'].iloc[0]),
                ic_original=(float(orig['lb']), float(orig['ub'])))


def kink(y, x, primeiro_estagio, c=0.0, h=None, p=1, cluster=None):
    """Fuzzy regression kink at c with rdrobust (deriv=1): slope change of y over slope change of the first
    stage, with robust bias-corrected inference. Also the sharp kink of each, separately."""
    from rdrobust import rdrobust
    kw = dict(c=c, deriv=1, p=p, kernel='triangular')
    if h is not None:
        kw['h'] = h
    if cluster is not None:
        kw['cluster'] = cluster
    f = rdrobust(_arr(y), _arr(x), fuzzy=_arr(primeiro_estagio), **kw)
    ry = rdrobust(_arr(y), _arr(x), **kw)
    rf = rdrobust(_arr(primeiro_estagio), _arr(x), **kw)
    lin = lambda r, i: float(np.asarray(r.coef).ravel()[i])
    ic = lambda r: tuple(np.asarray(r.ci, dtype=float)[2])
    return dict(repasse=lin(f, 0), ic_repasse=ic(f), p_repasse=float(np.asarray(f.pv).ravel()[2]),
                ic_repasse_convencional=tuple(np.asarray(f.ci, dtype=float)[0]),
                kink_y=lin(ry, 0), ic_kink_y=ic(ry), kink_fs=lin(rf, 0), ic_kink_fs=ic(rf),
                h=float(np.asarray(f.bws).ravel()[0]), n=int(np.asarray(f.N_h).sum()))


def kink_placebo(y, x, limiares=(-0.10, -0.05, 0.05, 0.10), c=0.0, p=1):
    """Sharp kink in y at placebo thresholds. Each placebo uses only the observations on its own side of the
    true threshold c, so that the true kink does not enter its window."""
    from rdrobust import rdrobust
    y, x = _arr(y), _arr(x)
    linhas = []
    for cc in limiares:
        s = x > c if cc > c else x < c
        r = rdrobust(y[s], x[s], c=cc, deriv=1, p=p, kernel='triangular')
        linhas.append(dict(limiar=cc, kink=float(np.asarray(r.coef).ravel()[0]),
                           ic=tuple(np.asarray(r.ci, dtype=float)[2]), p=float(np.asarray(r.pv).ravel()[2])))
    return pd.DataFrame(linhas)


def densidade(x, c=0.0):
    """Density test of Cattaneo, Jansson and Ma (2020) at c (rddensity). Returns the p-value."""
    from rddensity import rddensity
    t = rddensity(_arr(x), c=c).test
    v = t['p_jk']
    return float(v.iloc[0] if hasattr(v, 'iloc') else v)


def permutacao_kink(y, x, c=0.0, h=0.2, excluir=0.05, n_placebo=200, seed=1):
    """Permutation test in the spirit of Ganong and Jager (2018): the change in slope of y at c (local linear,
    triangular kernel, bandwidth h) is compared with the changes at placebo thresholds drawn across the support
    of x, away from c. Returns the estimate at c and the share of placebo estimates at least as large."""
    y, x = _arr(y), _arr(x)

    def mudanca(cc):
        u = (x - cc) / h
        k = np.clip(1 - np.abs(u), 0, None)
        s = k > 0
        X = np.column_stack([np.ones(s.sum()), x[s] - cc, (x[s] >= cc), (x[s] - cc) * (x[s] >= cc)])
        b = np.linalg.lstsq(X * np.sqrt(k[s])[:, None], y[s] * np.sqrt(k[s]), rcond=None)[0]
        return b[3]
    rng = np.random.default_rng(seed)
    lo, hi = np.quantile(x, [0.05, 0.95])
    cand = rng.uniform(lo + h, hi - h, n_placebo * 3)
    cand = cand[np.abs(cand - c) > excluir + h][:n_placebo]
    real = mudanca(c)
    plac = np.array([mudanca(cc) for cc in cand])
    return dict(kink=real, p=float((np.abs(plac) >= abs(real)).mean()), placebos=len(plac))
