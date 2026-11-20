"""Download selected municipal revenues (DCA, Anexo I-C) from the Siconfi API (Tesouro Nacional).

For each municipality and year, keeps the gross realized revenue ("Receitas Brutas Realizadas") of:
current revenue (1.0.0.0.00.0.0), the municipal quota of the ICMS (1.7.2.8.01.1.0), transfers of the
Union's complementation to the Fundeb (1.7.1.8.09.0.0; VAAF and VAAT together), transfers from the
Fundeb (1.7.5.8.01.0.0) and total revenue. Used by the VAAT study: the 2019 ICMS share of current
revenue (a covariate of the pre-analysis plan) and the complementation recorded in 2021 (the data check
of the spending kink). One call per municipality and year; the script can be interrupted and resumed.
Usage: python 15_siconfi_receitas.py 2019 2021
Output: data/siconfi/receitas_<year>.csv (cod_ibge;cod_conta;valor;populacao), data/siconfi/done_receitas_<year>.txt
"""
import csv, os, sys, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import importlib.util

AQUI = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location('dca', os.path.join(AQUI, '01_siconfi_dca.py'))
dca = importlib.util.module_from_spec(spec); spec.loader.exec_module(dca)

CONTAS = {'RO1.0.0.0.00.0.0', 'RO1.7.2.8.01.1.0', 'RO1.7.1.8.09.0.0', 'RO1.7.5.8.01.0.0', 'TotalReceitas'}


def baixa(ano):
    done_path, csv_path = os.path.join(dca.OUT, f'done_receitas_{ano}.txt'), os.path.join(dca.OUT, f'receitas_{ano}.csv')
    done = set(open(done_path).read().split()) if os.path.exists(done_path) else set()
    todo = [m for m in dca.municipios() if str(m) not in done]
    lock = Lock()
    new = not os.path.exists(csv_path)
    fcsv, fdone = open(csv_path, 'a', newline=''), open(done_path, 'a')
    w = csv.writer(fcsv, delimiter=';')
    if new:
        w.writerow(['cod_ibge', 'cod_conta', 'valor', 'populacao'])
    q = urllib.parse.urlencode({'an_exercicio': ano, 'no_anexo': 'DCA-Anexo I-C'})

    def one(m):
        items, off = [], 0
        while True:
            d = dca.get(f'{dca.BASE}/dca?{q}&id_ente={m}&offset={off}')
            items += d['items']
            if not d.get('hasMore'):
                return m, items
            off += d['limit']
    t0, n = time.time(), 0
    with ThreadPoolExecutor(12) as ex:
        for fut in as_completed([ex.submit(one, m) for m in todo]):
            m, items = fut.result()
            with lock:
                for i in items:
                    if i['coluna'] == 'Receitas Brutas Realizadas' and i['cod_conta'] in CONTAS:
                        w.writerow([m, i['cod_conta'], i['valor'], i.get('populacao')])
                fdone.write(f'{m}\n'); n += 1
                if n % 500 == 0:
                    fcsv.flush(); fdone.flush(); print(ano, n, len(todo), f'{time.time()-t0:.0f}s', flush=True)
    fcsv.close(); fdone.close()
    rows = list(csv.reader(open(csv_path, newline=''), delimiter=';'))
    rows = [rows[0]] + sorted(rows[1:], key=lambda r: (int(r[0]), r[1], float(r[2])))
    csv.writer(open(csv_path, 'w', newline=''), delimiter=';').writerows(rows)
    print(ano, 'complete', n, flush=True)


if __name__ == '__main__':
    for a in sys.argv[1:]:
        baixa(int(a))
