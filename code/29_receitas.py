"""Exploratory, not in the pre-analysis plan, run after the results of stage 3: where the rise in total
education spending of high-dose networks came from.

1. Download (Siconfi API, DCA Annex I-C, 2015 to 2025) of the revenue lines needed to decompose it:
   current revenue, taxes, current transfers, the ICMS quota, the FPM, the transfers from the Fundeb and
   the Union's complementation to the Fundeb, the court-ordered payments of Fundef arrears (precatórios),
   ("Receitas Brutas Realizadas"), and the total deduction for
   the Fundeb (the municipality's own contribution to the state fund). Account codes change in 2018 and
   2022, so lines are identified by name. A municipality without a deduction line has the deduction and
   the net Fundeb missing, not zero.
2. Event studies (reference 2019, specification of script 22) of each component per student enrolled
   in 2019, in reais of 2025, next to total education spending on the same denominator and to the VAAT
   money predicted and received (treatment data, times the weighted enrollment of the 2021 VAAT). A fixed
   denominator makes the components add up and keeps the enrollment trend out of them.
Usage: python 29_receitas.py baixar 2015 ... 2025    then    python 29_receitas.py
Outputs: data/siconfi/receitas_ic_<year>.csv (not in the repository, about 90 MB; rebuilt by the download in
         about an hour), results/29_receitas.csv (components by municipality and year), results/29_evento_receitas.csv
"""
import csv, os, re, sys, time, json, urllib.parse, importlib.util, warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import numpy as np
import pandas as pd
from config import DADOS, RES

AQUI = os.path.dirname(os.path.abspath(__file__))
warnings.simplefilter('ignore')


def modulo(nome, arquivo):
    spec = importlib.util.spec_from_file_location(nome, os.path.join(AQUI, arquivo))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


dca = modulo('dca', '01_siconfi_dca.py')
NOMES = re.compile(r'Receitas Correntes\s*$|Impostos, Taxas e Contribuições de Melhoria\s*$|Transferências Correntes\s*$|'
                   r'Fundo de Manutenção|Cota-Parte do ICMS|Fundo de Participação dos Municípios', re.I)


def manter(i):
    nome = re.sub(r'^[\d.]+\s*-?\s*', '', i['conta']).strip()
    if i['coluna'] == 'Receitas Brutas Realizadas':
        return i['cod_conta'] == 'TotalReceitas' or bool(NOMES.search(nome))
    if i['coluna'] == 'Deduções - FUNDEB':
        return bool(re.match(r'Receitas Correntes\s*$', nome, re.I))
    return False


def baixar(ano):
    done_path, csv_path = os.path.join(dca.OUT, f'done_receitas_ic_{ano}.txt'), os.path.join(dca.OUT, f'receitas_ic_{ano}.csv')
    done = set(open(done_path).read().split()) if os.path.exists(done_path) else set()
    todo = [m for m in dca.municipios() if str(m) not in done]
    novo = not os.path.exists(csv_path)
    fcsv, fdone = open(csv_path, 'a', newline=''), open(done_path, 'a')
    w = csv.writer(fcsv, delimiter=';')
    if novo:
        w.writerow(['cod_ibge', 'cod_conta', 'conta', 'coluna', 'valor'])
    q = urllib.parse.urlencode({'an_exercicio': ano, 'no_anexo': 'DCA-Anexo I-C'})
    lock = Lock()

    def um(m):
        itens, off = [], 0
        while True:
            d = dca.get(f'{dca.BASE}/dca?{q}&id_ente={m}&offset={off}')
            itens += d['items']
            if not d.get('hasMore'):
                return m, itens
            off += d['limit']
    t0, n = time.time(), 0
    with ThreadPoolExecutor(12) as ex:
        for fut in as_completed([ex.submit(um, m) for m in todo]):
            m, itens = fut.result()
            with lock:
                for i in itens:
                    if manter(i):
                        w.writerow([m, i['cod_conta'], i['conta'], i['coluna'], i['valor']])
                fdone.write(f'{m}\n'); n += 1
                if n % 500 == 0:
                    fcsv.flush(); fdone.flush(); print(ano, n, len(todo), f'{time.time() - t0:.0f}s', flush=True)
    fcsv.close(); fdone.close()
    print(ano, 'complete', n, flush=True)


def componentes(ano):
    d = pd.read_csv(os.path.join(dca.OUT, f'receitas_ic_{ano}.csv'), sep=';')
    d['nome'] = d['conta'].str.replace(r'^[\d.]+\s*-?\s*', '', regex=True).str.strip()
    b = d[d['coluna'] == 'Receitas Brutas Realizadas']
    pega = lambda sel: b[sel].groupby('cod_ibge')['valor'].max()          # the parent line is the largest of its family
    fundo = b['nome'].str.contains('Fundo de Manutenção', case=False)
    judicial = fundo & b['nome'].str.contains('Judicial|precat', case=False)     # Fundef court-ordered payments (precatórios)
    compl = fundo & ~judicial & b['nome'].str.contains('Complementação', case=False)
    fundo = fundo & ~judicial
    out = pd.DataFrame({
        'receita_corrente': pega(b['nome'].str.match(r'Receitas Correntes\s*$', case=False) & b['cod_conta'].str.startswith('RO1')),
        'impostos': pega(b['nome'].str.match(r'Impostos, Taxas', case=False)),
        'transferencias_correntes': pega(b['nome'].str.match(r'Transferências Correntes\s*$', case=False) & b['cod_conta'].str.startswith('RO1')),
        'icms': pega(b['nome'].str.contains('Cota-Parte do ICMS', case=False)),
        'fpm': pega(b['nome'].str.contains('Fundo de Participação dos Municípios', case=False)),
        'fundeb_recebido': pega(fundo & ~compl),
        'complementacao_uniao': pega(compl),
        'precatorios_fundef': b[judicial].groupby('cod_ibge')['valor'].sum(),
    })
    ded = d[d['coluna'] == 'Deduções - FUNDEB'].groupby('cod_ibge')['valor'].max()
    out['deducao_fundeb'] = ded.reindex(out.index)
    rep = set(d['cod_ibge'])
    out = out.reindex(sorted(rep))
    for c in ('fundeb_recebido', 'complementacao_uniao', 'precatorios_fundef'):        # absent line: nothing received
        out[c] = out[c].fillna(0.0)
    # a municipality that reports no deduction line is left missing (some record it elsewhere)
    out['fundeb_liquido'] = out['fundeb_recebido'] - out['deducao_fundeb'].abs()
    return out.assign(ano=ano)


if __name__ == '__main__':
    if sys.argv[1:2] == ['baixar']:
        for a in sys.argv[2:]:
            baixar(int(a))
        sys.exit()
    est = modulo('est', '20_estimacao.py'); e22 = modulo('e22', '22_etapa3.py')
    W = e22.W_COLS
    ip = e22.g03.ipca_medio()
    anos = range(2015, 2026)
    if all(os.path.exists(os.path.join(dca.OUT, f'receitas_ic_{a}.csv')) for a in anos):
        comp = pd.concat([componentes(a) for a in anos]).reset_index().rename(columns={'index': 'cod_ibge'})
        comp.to_csv(os.path.join(RES, '29_receitas.csv'), sep=';', index=False, float_format='%.2f')
    else:            # the raw lines (about 90 MB) are not in the repository; the components are
        comp = pd.read_csv(os.path.join(RES, '29_receitas.csv'), sep=';')
    b = pd.read_csv(os.path.join(RES, '22_base.csv'), sep=';')
    b = b[b['habilitado_tarde'] == 0].copy()
    b['D'] = b['dose_previsto_2025']
    for a in anos:
        b[f'gasto_total_{a}'] = b[f'gasto_aluno_{a}'] * b[f'matriculas_{a}']      # reais of 2025
    p = b[['ibge', 'uf', 'regiao', 'D', 'matriculas_2019', 'mat_vaat'] + W + [f'gasto_total_{a}' for a in anos]].melt(
        id_vars=['ibge', 'uf', 'regiao', 'D', 'matriculas_2019', 'mat_vaat'] + W, var_name='ano', value_name='gasto_educacao')
    p['ano'] = p['ano'].str[-4:].astype(int)
    # VAAT money of each year, predicted and received (with the 2023 and 2024 adjustments), times the weighted
    # enrollment of the 2021 VAAT: treatment data only, the benchmark for the recorded complementation
    for tipo, col in (('vaat_previsto', 'previsto'), ('vaat_recebido', 'recebido_ajustado')):
        v = b.set_index('ibge')[[f'{col}_{a}' for a in range(2021, 2026)]]
        v.columns = range(2021, 2026)
        v = v.stack().rename(tipo).reset_index().rename(columns={'level_1': 'ano'})
        p = p.merge(v, on=['ibge', 'ano'], how='left')
        p[tipo] = p[tipo].fillna(0.0) * p['mat_vaat'] * (ip[2025] / p['ano'].map(ip))
    p = p.merge(comp, left_on=['ibge', 'ano'], right_on=['cod_ibge', 'ano'], how='left')
    series = ['gasto_educacao', 'fundeb_liquido', 'fundeb_recebido', 'deducao_fundeb', 'complementacao_uniao', 'vaat_previsto',
              'vaat_recebido', 'precatorios_fundef', 'receita_corrente', 'impostos', 'icms', 'fpm']
    den = p['matriculas_2019'].where(p['matriculas_2019'] > 0)
    for s in series:
        if s not in ('gasto_educacao', 'vaat_previsto', 'vaat_recebido'):   # these are already in reais of 2025
            p[s] = p[s] * (ip[2025] / p['ano'].map(ip))
        p[s] = (p[s].abs() if s == 'deducao_fundeb' else p[s]) / den
    p = p.rename(columns={'ibge': 'id', 'regiao': 'cluster'})
    out = []
    for s in series:
        es = est.estudo_evento(p, s, 'D', W, ano_ref=2019, wild_B=999, seed=2025)
        out.append(es['tabela'].assign(serie=s, p_pre_wild=es['p_pre_wild'], unidades=es['unidades'], n=es['n']))
    t = pd.concat(out, ignore_index=True)
    t.to_csv(os.path.join(RES, '29_evento_receitas.csv'), sep=';', index=False, float_format='%.4f')
    with pd.option_context('display.width', 250):
        print(t.pivot(index='ano', columns='serie', values='beta').round(1).to_string())
        print(t.groupby('serie')[['p_pre_wild', 'unidades']].first().to_string())
        m19 = p[p['ano'] == 2019]
        print('2019 means per enrolled student, positive dose:', m19[m19['D'] > 0][series].mean().round(0).to_dict())
