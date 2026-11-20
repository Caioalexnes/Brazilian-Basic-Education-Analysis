"""Download the public files used by the scripts into DADOS (default: ../data).

Inep's download server (download.inep.gov.br) does not send the intermediate certificate of its TLS
chain, so a plain download fails certificate verification. The intermediate certificate, issued by
GlobalSign to RNP, is public and included in certs/; it is added to the usual root certificates, and
verification stays on. Siconfi spending is downloaded by script 01 and selected revenues by script 15;
the IPCA, the 2020 population and the immediate geographic regions come from IBGE's APIs.
The Fundeb annual adjustment of 2025 (Portaria Interministerial MEC/MF nº 5/2026, with the VAAR by
municipality) comes from the FNDE site.
The VAAT files of script 13 (data/fnde/vaat/) come from the Câmara dos Deputados (Estudo Técnico
15/2021, whose annex reproduces the 2021 VAAT of every habilitated network) and from the FNDE (the
December portarias of 2021 to 2025, Annex III, and the adjustments of 2023 and 2024).
Usage: python 00_download.py
"""
import os, ssl, urllib.request
from config import DADOS

AQUI = os.path.dirname(os.path.abspath(__file__))
INEP = 'https://download.inep.gov.br/'
ARQUIVOS = {
    'inep/microdados_censo_escolar_2015.zip': INEP + 'dados_abertos/microdados_censo_escolar_2015.zip',
    'inep/microdados_censo_escolar_2016.zip': INEP + 'dados_abertos/microdados_censo_escolar_2016.zip',
    'inep/microdados_censo_escolar_2017.zip': INEP + 'dados_abertos/microdados_censo_escolar_2017.zip',
    'inep/microdados_censo_escolar_2018.zip': INEP + 'dados_abertos/microdados_censo_escolar_2018.zip',
    'inep/microdados_censo_escolar_2019.zip': INEP + 'dados_abertos/microdados_censo_escolar_2019.zip',
    'inep/microdados_censo_escolar_2020.zip': INEP + 'dados_abertos/microdados_censo_escolar_2020.zip',
    'inep/microdados_censo_escolar_2021.zip': INEP + 'dados_abertos/microdados_censo_escolar_2021.zip',
    'inep/microdados_censo_escolar_2022.zip': INEP + 'dados_abertos/microdados_censo_escolar_2022.zip',
    'inep/microdados_censo_escolar_2023.zip': INEP + 'dados_abertos/microdados_censo_escolar_2023.zip',
    'inep/microdados_censo_escolar_2024.zip': INEP + 'dados_abertos/microdados_censo_escolar_2024.zip',
    # the 2025 file name on Inep's server ends with an underscore
    'inep/microdados_censo_escolar_2025.zip': INEP + 'dados_abertos/microdados_censo_escolar_2025_.zip',
    'inep/divulgacao_anos_iniciais_municipios_2025.zip': INEP + 'ideb/resultados/divulgacao_anos_iniciais_municipios_2025.zip',
    'inep/divulgacao_anos_finais_municipios_2025.zip': INEP + 'ideb/resultados/divulgacao_anos_finais_municipios_2025.zip',
    'inep/divulgacao_brasil_ideb_2025.zip': INEP + 'ideb/resultados/divulgacao_brasil_ideb_2025.zip',
    'inep/INSE_2019_MUNICIPIOS.xlsx': INEP + 'informacoes_estatisticas/indicadores_educacionais/2019/nivel_socioeconomico/INSE_2019_MUNICIPIOS.xlsx',
    'inep/INSE_2023_municipios.xlsx': INEP + 'informacoes_estatisticas/indicadores_educacionais/2023/nivel_socioeconomico/INSE_2023_municipios.xlsx',
    'inep/microdados_saeb_2017.zip': INEP + 'microdados/microdados_saeb_2017.zip',
    'inep/microdados_saeb_2023.zip': INEP + 'microdados/microdados_saeb_2023.zip',
    'inep/indicadores/DSU_2019_MUNICIPIOS.zip': INEP + 'informacoes_estatisticas/indicadores_educacionais/2019/DSU_2019_MUNICIPIOS.zip',
    'inep/indicadores/DSU_2023_MUNICIPIOS.zip': INEP + 'informacoes_estatisticas/indicadores_educacionais/2023/DSU_2023_MUNICIPIOS.zip',
    'inep/indicadores/DSU_2025_MUNICIPIOS.zip': INEP + 'informacoes_estatisticas/indicadores_educacionais/2025/DSU_2025_MUNICIPIOS.zip',
    'inep/indicadores/HAD_2019_MUNICIPIOS.zip': INEP + 'informacoes_estatisticas/indicadores_educacionais/2019/HAD_2019_MUNICIPIOS.zip',
    'inep/indicadores/HAD_2023_MUNICIPIOS.zip': INEP + 'informacoes_estatisticas/indicadores_educacionais/2023/HAD_2023_MUNICIPIOS.zip',
    'inep/indicadores/HAD_2025_MUNICIPIOS.zip': INEP + 'informacoes_estatisticas/indicadores_educacionais/2025/HAD_2025_MUNICIPIOS.zip',
    'ipca_1737.json': 'https://apisidra.ibge.gov.br/values/t/1737/n1/all/v/2266/p/201501-202512',
    # IBGE: municipalities with their immediate geographic regions, and the 2020 population estimates
    'ibge_municipios.json': 'https://servicodados.ibge.gov.br/api/v1/localidades/municipios',
    'pop_2020.json': 'https://apisidra.ibge.gov.br/values/t/6579/n6/all/v/9324/p/2020',
    'fnde/portaria_interministerial_5_2026.pdf': 'https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/financiamento/'
        'fundeb/legislacao/2026/portaria-interministerial-mec-mf-no-5-de-29-de-abril-de-2026/@@download/file',
    # VAAT (script 13): 2021 VAAT of all habilitated networks, and the recipients of each year
    'fnde/vaat/et15_2021.pdf': 'https://www2.camara.leg.br/orcamento-da-uniao/estudos/2021/et-15_2021-complementacao_vaat_fundeb-2021-v2',
    'fnde/vaat/portaria_10_2021.pdf': 'https://www.fnde.gov.br/phocadownload/fnde/legislacao/portarias/2021/'
        'PORTARIA%20INTERMINISTERIAL%20N%2010%20DE%2020%20DE%20DEZEMBRO%20DE%202021.pdf',
    'fnde/vaat/portaria_6_2022.pdf': 'https://www.fnde.gov.br/phocadownload/fnde/legislacao/portarias/2022/'
        'Portaria%20Interministerial%20n%206%20de%2028.12.2022.pdf',
    'fnde/vaat/anexo3_portaria_7_2023.pdf': 'https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/financiamento/fundeb/2023-1/AnexoIIIPortariaInterm.n7de29.12.2023.pdf/@@display-file/file',
    'fnde/vaat/anexo3_portaria_13_2024.pdf': 'https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/financiamento/fundeb/2024/AnexoIIIPortariaInterm.n13de23.12.2024.pdf/@@display-file/file',
    'fnde/vaat/anexo3_portaria_13_2025.pdf': 'https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/financiamento/fundeb/2025-1/5a-publicacao-2013-portaria-mec-mf-no-13-de-29-de-dezembro-de-2025/'
        '3-vaat-vaat-min-e-complementacao-vaat-por-ente-federado.pdf/@@display-file/file',
    'fnde/vaat/acerto_vaat_2023_portaria_7_2026.xlsx': 'https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/financiamento/fundeb/2023-1/portaria-mec_mf-n-7-de-29-de-abril-de-2026/'
        'AcertodaComplementaoVAAT2023PortariaInt.72026.xlsx/@@download/file',
    'fnde/vaat/ajuste_vaat_2024_portaria_3_2025.xlsx': 'https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/financiamento/fundeb/2025-1/AjustedaComplementaoVAAT.xlsx/@@download/file',
}

if __name__ == '__main__':
    ctx = ssl.create_default_context()
    ctx.load_verify_locations(os.path.join(AQUI, '..', 'certs', 'rnp_icpedu_gr46_ov_tls_ca_2025.pem'))
    for destino, url in ARQUIVOS.items():
        caminho = os.path.join(DADOS, destino)
        if os.path.exists(caminho):
            continue
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        with urllib.request.urlopen(url, context=ctx, timeout=600) as r, open(caminho, 'wb') as f:
            f.write(r.read())
        print('ok', destino)
    for z in ('divulgacao_anos_iniciais_municipios_2025', 'divulgacao_anos_finais_municipios_2025', 'divulgacao_brasil_ideb_2025'):
        import zipfile
        zipfile.ZipFile(os.path.join(DADOS, 'inep', z + '.zip')).extractall(os.path.join(DADOS, 'inep'))
