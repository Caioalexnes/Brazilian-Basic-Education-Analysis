"""Figures and tables of the paper, from the results files of scripts 13 to 27. Reads no raw data except the
Ideb files and the enrollment by network (script 25) for the descriptive table.

Outputs: paper/figuras/f1 to f8 (.pdf and .png), paper/tabelas/t1 to t6 (.tex), results/28_numeros.json (every
number quoted in the text that is not in a table).
"""
import os, json, importlib.util, warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from config import DADOS, RES

AQUI = os.path.dirname(os.path.abspath(__file__))
PAPER = os.path.join(AQUI, '..', 'paper')
FIG, TAB = os.path.join(PAPER, 'figuras'), os.path.join(PAPER, 'tabelas')
for d in (FIG, TAB):
    os.makedirs(d, exist_ok=True)
warnings.simplefilter('ignore')

# palette: first three categorical slots of the reference palette (validated all-pairs, light mode), neutral grays
AZUL, LARANJA, AQUA = '#2a78d6', '#eb6834', '#1baf7a'
TINTA, TINTA2, CINZA, GRADE = '#0b0b0b', '#52514e', '#8a8984', '#e4e3df'
P75 = 5.0130
SD_N = {5: 0.5069, 9: 0.5740}
plt.rcParams.update({'font.size': 9, 'axes.edgecolor': CINZA, 'axes.labelcolor': TINTA2, 'xtick.color': TINTA2,
                     'ytick.color': TINTA2, 'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': True,
                     'grid.color': GRADE, 'grid.linewidth': 0.6, 'axes.axisbelow': True, 'legend.frameon': False,
                     'lines.linewidth': 1.6, 'savefig.bbox': 'tight', 'pdf.fonttype': 42})


def ler(nome):
    return pd.read_csv(os.path.join(RES, nome), sep=';')


def salvar(fig, nome):
    fig.savefig(os.path.join(FIG, nome + '.pdf'))
    fig.savefig(os.path.join(FIG, nome + '.png'), dpi=200)
    plt.close(fig)


def evento(ax, t, cor, rotulo, marcador='o', deslocamento=0.0, escala=1.0, ref=2019):
    t = pd.concat([t[['ano', 'beta', 'se']], pd.DataFrame([dict(ano=ref, beta=0.0, se=0.0)])]).sort_values('ano')
    x = t['ano'] + deslocamento
    ax.errorbar(x, t['beta'] * escala, yerr=1.96 * t['se'] * escala, color=cor, marker=marcador, ms=4, lw=1.4, capsize=0,
                elinewidth=1.0, label=rotulo)
    ax.axhline(0, color=CINZA, lw=0.8)
    ax.axvline(ref, color=CINZA, lw=0.8, ls=':')


def f(v, d=3):
    if pd.isna(v):
        return ''
    return ('$-$' if v < 0 and round(abs(v), d) > 0 else '') + f'{abs(v):,.{d}f}'.replace(',', '{,}')


def n(v):
    return f'{int(v):,}'.replace(',', '{,}')


ROB = {'1': 'No covariates', '3': '2019 level as covariate', '4': 'Excluding Ceará', '5': 'Trimming the 1\\% tails of the change',
       '6': 'Zero-dose networks only if $x \\le 0.3$', '7a': 'Dose from money received', '7b': '$g_t$ from Fundeb revenue growth',
       '7c': 'Dose in nominal reais', '7d': 'Dose per enrolled student', '8': 'Including the 105 late recipients',
       '9': 'Weighted by 2019 enrollment', '10': 'Heteroskedasticity-robust errors'}


def estrelas(p):
    return '' if pd.isna(p) else ('$^{***}$' if p < 0.01 else '$^{**}$' if p < 0.05 else '$^{*}$' if p < 0.1 else '')


def tabela(nome, cab, linhas, nota, alinhamento):
    corpo = '\n'.join(linhas)
    open(os.path.join(TAB, nome + '.tex'), 'w').write(
        f'\\begin{{adjustbox}}{{max width=\\linewidth}}\n\\begin{{tabular}}{{{alinhamento}}}\n\\toprule\n{cab} \\\\\n\\midrule\n'
        f'{corpo}\n\\bottomrule\n\\end{{tabular}}\n\\end{{adjustbox}}\n'
        f'\\par\\smallskip\\begin{{minipage}}{{0.95\\linewidth}}\\footnotesize {nota}\\end{{minipage}}\n')


if __name__ == '__main__':
    num = {}
    anos = ler('13_vaat_anos.csv')
    base = ler('22_base.csv')
    a = base[base['habilitado_tarde'] == 0].copy()

    # F1: money and recipients by year (two measures, two panels)
    fig, ax = plt.subplots(1, 2, figsize=(6.5, 2.4))
    fig.subplots_adjust(wspace=0.35)
    ax[0].bar(anos['ano'], anos['total_bi'], color=AZUL, width=0.6)
    ax[0].set_title('a. VAAT complementation (R\\$ billion)', fontsize=9, color=TINTA, loc='left')
    ax[1].bar(anos['ano'], anos['municipios'], color=AZUL, width=0.6)
    ax[1].set_title('b. Municipal networks that received', fontsize=9, color=TINTA, loc='left')
    for k in ax:
        k.set_xticks(anos['ano']); k.grid(axis='x', visible=False)
    for i, r in anos.iterrows():
        ax[0].text(r['ano'], r['total_bi'], f"{r['total_bi']:.1f}", ha='center', va='bottom', fontsize=7, color=TINTA2)
        ax[1].text(r['ano'], r['municipios'], f"{int(r['municipios']):,}", ha='center', va='bottom', fontsize=7, color=TINTA2)
    salvar(fig, 'f1_vaat_anos')

    # F2: dose against the 2021 VAAT position
    fig, ax = plt.subplots(figsize=(4.2, 2.8))
    s = a[a['x'] <= 1.0]
    ax.scatter(s['x'], s['dose_previsto_2025'], s=3, color=AZUL, alpha=0.35, lw=0)
    ax.axvline(0, color=CINZA, lw=0.8, ls=':')
    ax.set_xlabel('Position x = VAAT 2021 / VAAT-MIN 2021 - 1')
    ax.set_ylabel('Predicted dose (R\\$ 1,000 of 2025\nper weighted student, 2021-2025)')
    salvar(fig, 'f2_dose_posicao')

    # F3: event studies of spending per student, ln spending and ln enrollment
    e22 = ler('22_evento_gasto.csv'); e24 = ler('24_gasto_exploratorio.csv')
    mec = e24[e24['analise'] == 'mechanical benchmark']
    fig, ax = plt.subplots(1, 3, figsize=(7.2, 2.5))
    evento(ax[0], e22, AZUL, 'Estimate')
    ax[0].scatter(mec['ano'], mec['beta'], s=18, facecolors='none', edgecolors=LARANJA, lw=1.2, zorder=3,
                  label='Predicted VAAT money')
    ax[0].set_title('a. Spending per student (R\\$)', fontsize=9, color=TINTA, loc='left')
    ax[0].legend(fontsize=7, loc='lower left')
    evento(ax[1], e24[e24['analise'] == 'ln spending'], AZUL, '', escala=100)
    mecp = e24[e24['analise'] == 'mechanical benchmark, percent of 2019 spending']
    ax[1].scatter(mecp['ano'], mecp['beta'], s=18, facecolors='none', edgecolors=LARANJA, lw=1.2, zorder=3)
    ax[1].set_title('b. ln spending (x 100)', fontsize=9, color=TINTA, loc='left')
    evento(ax[2], e24[e24['analise'] == 'ln enrollment'], AZUL, '', escala=100)
    ax[2].set_title('c. ln enrollment (x 100)', fontsize=9, color=TINTA, loc='left')
    for k in ax:
        k.set_xticks([2015, 2017, 2019, 2021, 2023, 2025]); k.tick_params(axis='x', labelsize=7)
    fig.tight_layout()
    salvar(fig, 'f3_evento_gasto')

    # F4: enrollment by network (fundamental, early and late grades)
    e25 = ler('25_evento_matriculas.csv')
    fig, ax = plt.subplots(1, 2, figsize=(6.5, 2.5), sharey=True)
    for k, (etapa, titulo) in zip(ax, (('fund_ai', 'a. Early grades of fundamental'), ('fund_af', 'b. Late grades of fundamental'))):
        for (rede, cor, rot, m, dx) in (('municipal', AZUL, 'Municipal network', 'o', -0.15), ('estadual', LARANJA, 'State network', 's', 0.0),
                                       ('total', AQUA, 'All networks', '^', 0.15)):
            evento(k, e25[e25['serie'] == f'ln_{etapa}_{rede}'], cor, rot, marcador=m, deslocamento=dx, escala=100)
        k.set_title(titulo + ' (ln x 100)', fontsize=9, color=TINTA, loc='left')
        k.set_xticks([2015, 2017, 2019, 2021, 2023, 2025]); k.tick_params(axis='x', labelsize=7)
    ax[0].legend(fontsize=7, loc='lower left')
    fig.tight_layout()
    salvar(fig, 'f4_matriculas_redes')

    # F8: municipal creche enrollment
    fig, ax = plt.subplots(figsize=(4.2, 2.6))
    evento(ax, e25[e25['serie'] == 'ln_creche_municipal'], AZUL, '', escala=100)
    ax.set_xticks([2015, 2017, 2019, 2021, 2023, 2025])
    ax.set_title('Municipal creche enrollment (ln x 100)', fontsize=9, color=TINTA, loc='left')
    salvar(fig, 'f8_creche')

    # F5: dose-response curve of spending per student
    c = ler('22_p1_curva.csv')
    fig, ax = plt.subplots(figsize=(4.2, 2.7))
    ax.fill_between(c['dose'], c['lo'], c['hi'], color=AZUL, alpha=0.15, lw=0)
    ax.plot(c['dose'], c['att'], color=AZUL)
    ax.axhline(0, color=CINZA, lw=0.8)
    ax.set_xlabel('Predicted dose (R\\$ 1,000 per weighted student)')
    ax.set_ylabel('ATT(d), change in spending\nper student 2019-2025 (R\\$)')
    salvar(fig, 'f5_curva_gasto')

    # F6: event studies of N with the linear pre-trend
    e26 = ler('26_evento.csv')
    fig, ax = plt.subplots(1, 2, figsize=(6.5, 2.6), sharey=True)
    for k, g in zip(ax, (5, 9)):
        t = e26[e26['analise'] == f'N {g}th grade']
        evento(k, t, AZUL, 'Estimate')
        pre = t[t['ano'].between(2009, 2017)]
        X = np.column_stack([np.ones(len(pre)), pre['ano'] - 2019])
        cf = np.linalg.lstsq(X, pre['beta'], rcond=None)[0]
        xs = np.arange(2005, 2026)
        k.plot(xs, cf[0] + cf[1] * (xs - 2019), color=LARANJA, ls='--', lw=1.2, label='Linear trend, 2009-2017')
        k.set_title(f'{"a" if g == 5 else "b"}. N, {g}th grade (points per R\\$ 1,000)', fontsize=9, color=TINTA, loc='left')
        k.set_xticks(list(range(2005, 2026, 4))); k.tick_params(axis='x', labelsize=7)
        num[f'trend_slope_{g}'] = float(cf[1] * 2)
    ax[0].legend(fontsize=7, loc='upper left')
    fig.tight_layout()
    salvar(fig, 'f6_evento_N')

    # F7: learning estimates at the 75th percentile of the dose, in student SD
    p2 = ler('26_p2.csv'); dentro = ler('26_dentro.csv'); poder = ler('14_poder.csv').set_index(ler('14_poder.csv').columns[0])['valor']
    linhas = []
    for g in (5, 9):
        r = p2[p2['grade'] == g].iloc[0]
        linhas.append((f'{g}th grade: long difference (plan)', r['beta_p75_dp'], r['lo_p75_dp'], r['hi_p75_dp']))
        t = e26[(e26['analise'] == f'N {g}th grade') & (e26['ano'] == 2025)].iloc[0]
        b, se = t['beta2025_menos_tendencia'], t['se_menos_tendencia']
        k = P75 * SD_N[g]
        linhas.append((f'{g}th grade: event study net of linear trend', b * k, (b - 1.96 * se) * k, (b + 1.96 * se) * k))
        w = dentro[dentro['especificacao'] == f'within municipality (municipal minus state), {g}th grade'].iloc[0]
        linhas.append((f'{g}th grade: within municipality', w['beta_p75_dp'], w['lo_p75_dp'], w['hi_p75_dp']))
        num[f'trend_corrected_{g}_sd'] = [b * k, (b - 1.96 * se) * k, (b + 1.96 * se) * k]
    fig, ax = plt.subplots(figsize=(5.4, 2.8))
    for i, (rot, b, lo, hi) in enumerate(linhas[::-1]):
        ax.plot([lo, hi], [i, i], color=AZUL, lw=1.4)
        ax.plot(b, i, 'o', color=AZUL, ms=5)
    ax.set_yticks(range(len(linhas))); ax.set_yticklabels([l[0] for l in linhas[::-1]], fontsize=7.5)
    ax.axvline(0, color=CINZA, lw=0.8)
    esperado = poder['efeito_esperado_dp_aluno']
    ax.axvline(esperado, color=LARANJA, lw=1.0, ls='--')
    ax.text(esperado, len(linhas) - 0.4, ' expected under U.S. returns', color=TINTA2, fontsize=7, va='center')
    ax.set_xlabel('Effect at the 75th percentile of the dose (student standard deviations)')
    ax.grid(axis='y', visible=False)
    salvar(fig, 'f7_aprendizagem')

    # T1: descriptive statistics by dose group
    m25 = ler('25_matriculas_redes.csv')
    m19 = m25[m25['ano'] == 2019].pivot_table(index='cod_ibge', columns='rede', values=['fund_ai', 'fund_af'], aggfunc='sum', fill_value=0)
    est_fund = (m19[('fund_ai', 'estadual')] + m19[('fund_af', 'estadual')])
    pub_fund = sum(m19[(e, r)] for e in ('fund_ai', 'fund_af') for r in ('estadual', 'municipal') if (e, r) in m19.columns)
    a['parcela_estadual'] = a['ibge'].map(est_fund / pub_fund.where(pub_fund > 0))
    a['cresc_mat'] = 100 * np.log(a['matriculas_2019'] / a['matriculas_2015'])
    ideb_n = {}
    for g, nome in ((5, 'divulgacao_anos_iniciais_municipios_2025'), (9, 'divulgacao_anos_finais_municipios_2025')):
        x = pd.read_excel(os.path.join(DADOS, 'inep', nome, nome + '.xlsx'), header=9)
        x = x[x['REDE'] == 'Municipal']
        a[f'N{g}_2019'] = a['ibge'].map(pd.Series(pd.to_numeric(x['VL_NOTA_MEDIA_2019'], errors='coerce').values,
                                                   index=pd.to_numeric(x['CO_MUNICIPIO'], errors='coerce')))
    pos = a['dose_previsto_2025'] > 0
    terc = pd.qcut(a.loc[pos, 'dose_previsto_2025'], 3, labels=['low', 'middle', 'high'])
    a['grupo'] = 'zero'
    a.loc[pos, 'grupo'] = terc.astype(str)
    a['pop_mil'] = np.exp(a['ln_pop_2020']) / 1000
    vars_ = [('Networks', None, 0), ('VAAT 2021 (R\\$ per weighted student)', 'vaat2021', 0),
             ('Predicted dose (R\\$ 1,000)', 'dose_previsto_2025', 2), ('Spending per student 2019 (R\\$ of 2025)', 'gasto_aluno_2019', 0),
             ('Municipal enrollment 2019', 'matriculas_2019', 0), ('Enrollment growth 2015-2019 (log points x 100)', 'cresc_mat', 1),
             ('State share of public fundamental enrollment 2019', 'parcela_estadual', 2), ('INSE 2019', 'inse_2019', 2),
             ('Population 2020 (thousands, median)', 'pop_mil', 1), ('Northeast', 'nordeste', 2), ('N, 5th grade, 2019', 'N5_2019', 2),
             ('N, 9th grade, 2019', 'N9_2019', 2)]
    grupos = ['zero', 'low', 'middle', 'high']
    linhas = []
    for rot, col, d in vars_:
        cel = []
        for gr in grupos:
            s = a[a['grupo'] == gr]
            if col is None:
                cel.append(f'{len(s):,}'.replace(',', '{,}'))
            elif col == 'pop_mil':
                cel.append(f(s[col].median(), d))
            else:
                cel.append(f(s[col].mean(), d))
        linhas.append(rot + ' & ' + ' & '.join(cel) + ' \\\\')
    tabela('t1_descritivas', 'Dose group & Zero & Low & Middle & High', linhas,
           'Means over the 5,208 municipal networks of the main sample, unless stated. Low, middle and high are terciles of the '
           'positive predicted dose. Enrollment growth: municipal-network enrollment, Censo Escolar. N: standardized Saeb mean '
           'of the municipal network (0 to 10).', 'lrrrr')
    num['t1_cresc_mat'] = a.groupby('grupo')['cresc_mat'].mean().to_dict()

    # T2: spending per student (P1)
    p1 = ler('22_p1.csv'); rb = ler('22_p1_robustez.csv')
    linhas = []
    r = p1.iloc[0]
    linhas.append(f'Long difference, $\\beta$ & {f(r.beta, 1)}{estrelas(r.p)} & ({f(r.se, 1)}) & [{f(r.lo, 1)}, {f(r.hi, 1)}] & {n(r.n)} \\\\')
    for i, nome in ((1, 'ATT$^o$'), (2, 'Mean of $h\'(D)$ over the treated')):
        r = p1.iloc[i]
        linhas.append(f'{nome} & {f(r.beta, 1)} & ({f(r.se, 1)}) & [{f(r.lo, 1)}, {f(r.hi, 1)}] & {n(r.n)} \\\\')
    r = p1.iloc[3]
    linhas.append(f'Mechanical benchmark & {f(r.beta, 1)} & ({f(r.se, 1)}) & & \\\\')
    linhas.append('\\midrule')
    for _, r in rb.iloc[1:].iterrows():
        k_ = r['especificacao'].split(' ', 1)[0]
        linhas.append(f'({k_}) {ROB[k_]} & {f(r.beta, 1)}{estrelas(r.p)} & ({f(r.se, 1)}) & [{f(r.lo, 1)}, {f(r.hi, 1)}] & {n(r.n)} \\\\')
    tabela('t2_gasto', 'Specification & Estimate & (SE) & 95\\% interval & Networks', linhas,
           'Change in spending per student from 2019 to 2025, in reais of 2025, per R\\$ 1,000 of cumulative predicted dose. State '
           'fixed effects; covariates INSE 2019, ln population 2020 and ICMS share 2019; errors clustered by immediate region '
           '(509 clusters). ATT$^o$ and $h\'$: cubic B-spline in the dose, bootstrap over immediate regions (999 draws). '
           'Mechanical benchmark: predicted 2025 VAAT money per enrolled student regressed on the dose with the same specification. '
           'Robustness rows follow the numbering of Section 8 of the plan. $^{*}$ $p<0.1$, $^{**}$ $p<0.05$, $^{***}$ $p<0.01$.', 'lrrcr')

    # T3: S2
    s2 = ler('22_s2.csv')
    nomes = {'gasto_infantil_aluno': 'Spending per student, early childhood (R\\$)', 'gasto_fundamental_aluno': 'Spending per student, fundamental (R\\$)',
             'ln_mat_creche': 'ln enrollment, creche', 'ln_mat_pre': 'ln enrollment, pre-school', 'integral_creche': 'Full-time share, creche',
             'integral_pre': 'Full-time share, pre-school', 'integral_fundamental': 'Full-time share, fundamental',
             'alunos_turma_ai': 'Students per class, early grades', 'docentes_100_alunos': 'Teachers per 100 students',
             'superior_infantil': 'Teachers with higher education, early childhood (\\%)',
             'superior_fundamental': 'Teachers with higher education, fundamental (\\%)', 'horas_creche': 'Daily hours, creche',
             'horas_pre': 'Daily hours, pre-school', 'horas_fundamental_ai': 'Daily hours, early grades'}
    linhas = []
    for c, rot in nomes.items():
        cel = []
        for ano in (2023, 2025):
            r = s2[(s2['desfecho'] == c) & (s2['ano'] == ano)].iloc[0]
            d = 1 if c.startswith('gasto') else 4
            cel.append(f'{f(r.beta, d)} & ({f(r.se, d)}) & {f(r.q_bh, 3)}')
        linhas.append(rot + ' & ' + ' & '.join(cel) + ' \\\\')
    tabela('t3_insumos', ' & \\multicolumn{3}{c}{2019 to 2023} & \\multicolumn{3}{c}{2019 to 2025} \\\\\n\\cmidrule(lr){2-4}\\cmidrule(lr){5-7}\n'
           'Outcome & $\\beta$ & (SE) & $q$ & $\\beta$ & (SE) & $q$', linhas,
           'Change from 2019, per R\\$ 1,000 of predicted dose (summed up to the outcome year). Specification as in Table 2. '
           '$q$: Benjamini-Hochberg over the 28 tests.', 'lrrrrrr')

    # T4: learning (P2 and S1)
    s1 = ler('26_s1.csv')
    linhas = []
    for g in (5, 9):
        r = p2[p2['grade'] == g].iloc[0]
        linhas.append(f'N, {g}th grade (P2) & {f(r.beta, 4)} & ({f(r.se, 4)}) & {f(r.p_holm, 3)} & {f(r.beta_p75_dp, 3)} & [{f(r.lo_p75_dp, 3)}, {f(r.hi_p75_dp, 3)}] \\\\')
    linhas.append('\\midrule')
    rot = {'ideb': 'Ideb', 'mat': 'Mathematics (points)', 'por': 'Portuguese (points)', 'P': 'Flow indicator P', 'N': 'N, 2019 to 2023', 'INSE': 'INSE of the network, 2019 to 2023'}
    for _, r in s1.iterrows():
        nome = rot[r['desfecho']] + ('' if pd.isna(r['grade']) else f', {int(r["grade"])}th grade')
        d = 3 if r['desfecho'] in ('mat', 'por') else 4
        linhas.append(f'{nome} & {f(r.beta, d)} & ({f(r.se, d)}) & {f(r.q_bh, 3)} & {f(r.beta_p75_dp, 3)} & \\\\')
    tabela('t4_aprendizagem', 'Outcome & $\\beta$ & (SE) & Adjusted $p$ & At p75, SD & 95\\% interval at p75, SD', linhas,
           'Change from 2019 to 2025 unless stated, per R\\$ 1,000 of predicted dose. Specification as in Table 2. P2: Holm-adjusted '
           '$p$ across the two grades; S1 (below the line): Benjamini-Hochberg $q$ over 11 tests. SD: student standard deviations '
           '(one point of N is 0.507 SD in the 5th grade and 0.574 in the 9th; scores use the student SD of public schools in 2023).', 'lrrrrc')

    # T5: within municipality
    linhas = []
    for _, r in dentro.iterrows():
        nome = r['especificacao'].rsplit(',', 1)[0]
        nome = nome[0].upper() + nome[1:]
        linhas.append(f'{nome}, {int(r.grade)}th grade & {f(r.beta, 4)} & ({f(r.se, 4)}) & {f(r.beta_p75_dp, 3)} & [{f(r.lo_p75_dp, 3)}, {f(r.hi_p75_dp, 3)}] & {int(r.n)} \\\\')
    tabela('t5_dentro', 'Outcome & $\\beta$ & (SE) & At p75, SD & 95\\% interval & Municipalities', linhas,
           'Change in N from 2019 to 2025, municipalities where both the municipal and the state network have N in 2019 and 2025. '
           'Specification as in Table 2.', 'lrrrcr')

    # T6: kink
    k = ler('23_kink.csv')
    linhas = []
    for _, r in k.iterrows():
        if r['teste'].startswith(('first-stage', 'reduced-form')):
            continue
        nome = r['teste'][0].upper() + r['teste'][1:]
        est_ = f(r.estimativa, 2) if r['tipo'] != 'density' else ''
        ic = f'[{f(r.lo, 2)}, {f(r.hi, 2)}]' if pd.notna(r['lo']) else ''
        linhas.append(f'{nome} & {est_} & {ic} & {f(r.p, 3)} \\\\')
    tabela('t6_kink', 'Test & Estimate & Robust 95\\% interval & $p$', linhas,
           'Fuzzy regression kink at the 2021 threshold (\\texttt{rdrobust}, local linear, triangular kernel, MSE-optimal bandwidth '
           'unless stated). Outcome: change in education spending per enrolled student between 2018-2019 and 2021-2022, reais of 2021. '
           'Pass-through: reais of spending per real of 2021 complementation. Sharp kinks for predetermined variables and placebo thresholds.', 'lrcr')

    # numbers quoted in the text
    num['p75'] = P75
    num['efeito_esperado_dp'] = float(esperado)
    num['mde_5ano_dp'] = float(poder['mde_5ano_dp_aluno'])
    json.dump(num, open(os.path.join(RES, '28_numeros.json'), 'w'), indent=1, default=float)
    print(json.dumps(num, indent=1, default=float))
