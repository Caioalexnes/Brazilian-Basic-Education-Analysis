"""Saeb participation of the public schools of each municipality, 5th and 9th grades, 2017 and 2023.

Participation = students present in the Saeb over students enrolled according to the Censo Escolar,
summed over the public schools of the municipality (school files TS_ESCOLA). The Saeb school files
identify public schools (IN_PUBLICA) but not their network, so municipal and state schools are pooled,
as the pre-analysis plan specifies. The plan uses 2025 if its school files are released before the
analysis; in November 2026 Inep had released the Saeb microdata up to 2023, so 2023 is the post round.
The public school files mask the municipality and school identifiers: ID_MUNICIPIO is a sequential code
that changes between editions and does not match the IBGE code (nor ID_ESCOLA the Censo code). The output
is therefore by masked municipality (id_municipio_saeb) and cannot be linked to the treatment data; the
participation outcome of the plan is not estimated (pap/detalhes_etapa4.md, item 3).
Inputs: data/inep/microdados_saeb_2017.zip, data/inep/microdados_saeb_2023.zip
Output: results/17_participacao_saeb.csv (ano;id_municipio_saeb;etapa;escolas;matriculados;presentes;participacao)
"""
import os, zipfile
import pandas as pd
from config import DADOS, RES

ARQ = {2017: 'DADOS/TS_ESCOLA.csv', 2023: 'MICRODADOS_SAEB_2023/DADOS/TS_ESCOLA.csv'}

if __name__ == '__main__':
    partes = []
    for ano, nome in ARQ.items():
        z = zipfile.ZipFile(os.path.join(DADOS, 'inep', f'microdados_saeb_{ano}.zip'))
        linha = z.open(nome).readline().decode('latin1')
        sep = ',' if linha.count(',') > linha.count(';') else ';'
        cols = ['ID_MUNICIPIO', 'IN_PUBLICA'] + [f'NU_{c}_{e}' for c in ('MATRICULADOS_CENSO', 'PRESENTES') for e in ('5EF', '9EF')]
        d = pd.read_csv(z.open(nome), sep=sep, encoding='latin1', usecols=cols, low_memory=False)
        d = d[d['IN_PUBLICA'] == 1]
        for e in ('5EF', '9EF'):
            m = pd.to_numeric(d[f'NU_MATRICULADOS_CENSO_{e}'], errors='coerce')
            p = pd.to_numeric(d[f'NU_PRESENTES_{e}'], errors='coerce')
            ok = m > 0
            g = pd.DataFrame({'id_municipio_saeb': d.loc[ok, 'ID_MUNICIPIO'], 'm': m[ok], 'p': p[ok].fillna(0)}).groupby('id_municipio_saeb')
            t = pd.DataFrame({'escolas': g.size(), 'matriculados': g['m'].sum(), 'presentes': g['p'].sum()})
            t['participacao'] = t['presentes'] / t['matriculados']
            partes.append(t.reset_index().assign(ano=ano, etapa=e))
    r = pd.concat(partes, ignore_index=True)[['ano', 'id_municipio_saeb', 'etapa', 'escolas', 'matriculados', 'presentes', 'participacao']]
    r = r.sort_values(['ano', 'etapa', 'id_municipio_saeb'])
    r.to_csv(os.path.join(RES, '17_participacao_saeb.csv'), sep=';', index=False, float_format='%.4f')
    print(r.groupby(['ano', 'etapa']).agg(municipios=('id_municipio_saeb', 'size'), mediana=('participacao', 'median'),
                                          total=('presentes', 'sum')).round(3).to_string())
