# Where does federal equalization money go? Brazil's Fundeb VAAT

Code and data for a paper in preparation by Caio A. F. Cunha (independent researcher, ORCID
[0009-0008-2153-901X](https://orcid.org/0009-0008-2153-901X)) on the spending per student and the
learning outcomes of Brazil's municipal school networks, and on the federal VAAT complementation of
the Fundeb, which since 2021 tops up every network whose resources per weighted student fall below a
national minimum.

The repository has two parts:

1. **Descriptive** (scripts 01 to 03 and 08): the relation between spending per student and the Ideb of
   the municipal networks from 2017 to 2025, net of the students' socioeconomic level, and a test of
   whether the larger 2025 coefficient measures an effect of money or money going to networks that
   were already doing well.
2. **Causal** (`pap/`, scripts 13 and 14): the treatment data of the VAAT complementation from 2021 to
   2025 and the pre-analysis plan of a study of its effects on spending, school inputs and learning.
   The outcome regressions will be added only after the plan is deposited.

The descriptive scripts were first written for the essay *Dinheiro dos Outros nos Outros*, whose
repository is [Others-money-on-others](https://github.com/Caioalexnes/Others-money-on-others). All data
are public.

## Descriptive results

Spending per student of the municipal network (2023 reais) and the Ideb of the network's early
grades (5th grade, *anos iniciais*), one observation per municipality. Coefficients are Ideb points
per R$ 1,000 per student per year, with heteroskedasticity-robust standard errors.

| Year | Municipalities | Without controls | With the students' socioeconomic level (INSE) | Todos Pela Educação, without controls |
|---|---|---|---|---|
| 2017 | 5,165 | 0.166 (0.005) | 0.025 (0.004) | 0.16 |
| 2019 | 5,110 | 0.131 (0.005) | 0.012 (0.004) | 0.12 |
| 2023 | 5,229 | 0.053 (0.013) | 0.006 (0.003) | 0.06 |
| 2025 | 5,261 | 0.052 (0.004) | 0.020 (0.003) | |

For the late grades (9th grade, *anos finais*) the coefficients without controls are 0.137, 0.087 and
0.032, against 0.13, 0.08 and 0.05 in Todos Pela Educação; with the INSE, the 2023 coefficient is
0.001 (0.002), and the 2025 coefficients are 0.045 and 0.022 (0.004). The enrollment-weighted mean
spending per student in 2023 is R$ 12,589, against R$ 12,460 in Todos Pela Educação; in 2025 it is
R$ 14,405 (2023 reais), 66% above 2017. Within each band of R$ 2,000 of spending per student, the Ideb of the
early grades varies by about 2 points between the 10th and the 90th percentile, while the mean of the
highest-spending band (above R$ 20,000, mean 6.31) is about 1 point above that of the lowest
(below R$ 8,000, mean 5.28). See `results/03_regressoes.csv` and `results/03_faixas.csv`.

### 2025: the coefficient rises, but money also follows results

The INSE of the 2025 Saeb had not been released in November 2026, so the 2023 edition is used for
2025. The lag does not explain the rise: using the 2019 INSE in 2023 gives 0.009 instead of 0.006.
The 2025 coefficient comes from the Saeb scores, not from approval rates, and it does not depend on
the networks with implausible scores: without Ceará, Alagoas and the 57 networks with a 5th-grade
mathematics mean above 300 in any year, it is 0.018; by median regression, 0.016.

It does not measure an effect of money, though. Holding the 2023 spending and the INSE fixed, the
2025 spending is associated with the Ideb of 2023, measured before the money arrived, almost as much
as with the Ideb of 2025 (0.039 and 0.044 per R$ 1,000); from 2019 to 2023 the pattern is the same
(0.028 for the 2019 Ideb, 0.015 for the 2023 Ideb). Part of this is by design: since Constitutional
Amendment 108 (2020) part of the municipal ICMS is distributed by learning indicators, and the Fundeb
has a part paid by results (complementação VAAR), R$ 5.1 billion in 2025 for 2,833 municipalities.
The VAAR alone is too small to explain it (about R$ 370 per student, 2.5% of spending; spending net of
VAAR gives 0.019). Between 2023 and 2025, spending per student rose R$ 3.2 thousand in the fifth of
networks with the poorest students and R$ 1.3 thousand in the richest fifth, and the Ideb rose 0.57
and 0.22 points. In 2025, 31 municipal networks had a 5th-grade mathematics mean above 320 (none in
2019), 23 of them in Ceará; the national mean of private schools was 254. See
`results/08_resultados.csv`, `results/08_notas_altas.csv` and `results/08_vaar_2025.csv`.

## Pre-analysis plan: the VAAT complementation

`pap/vaat_pap.tex` (and its PDF) pre-specifies the causal analysis of the VAAT complementation of the
Fundeb: since 2021 the Union tops up every school network whose resources per weighted student fall
below a national minimum. The main design is a difference-in-differences with a continuous dose, the
complementation that the legal formula predicts from the 2021 VAAT of each network, which uses 2019
revenues; a comparison between the municipal and the state network of the same municipality; and a
regression kink at the 2021 threshold for spending. The plan was written before any outcome was
related to the treatment. Scripts 13 and 14 reproduce every number in it and use no outcome data in
relation to the dose. The outcome regressions will be added only after the plan is deposited.
Version 2.0 of the plan was deposited on Zenodo on 20 November 2026,
[doi:10.5281/zenodo.24391651](https://doi.org/10.5281/zenodo.24391651); it is the file
`pap/vaat_pap.pdf` of commit `06ba1ca` (tag `pap-v2.0`) of this repository.

The 2021 VAAT of the 5,234 networks habilitated by mid-2021 comes from the annex of the Câmara's
Estudo Técnico 15/2021, which reproduces Portarias Interministeriais 3/2021 and 4/2021. For the 1,422
recipients that are also in the official December 2021 list (Portaria 10/2021), the two sources agree
to within 0.024%. Another 105 recipients were habilitated later and are kept apart.

## Scripts (`code/`)

| Script | What it does | Output |
|---|---|---|
| `00_download.py` | Downloads the Inep files, the IPCA and the Fundeb files of the FNDE and the Câmara (see the note on Inep's certificate below) | `data/` |
| `01_siconfi_dca.py` | Downloads, for every municipality, the expenditure by function of the Declaração de Contas Anuais (DCA, Anexo I-E) from the Siconfi API of the Tesouro Nacional, keeping function 12 (Educação), its subfunctions and subfunction 847 | `data/siconfi/dca_<year>.csv` |
| `02_matriculas.py` | Enrollments of each municipal network in the Censo Escolar: basic-education enrollments of municipal schools in activity, plus early-childhood enrollments of private schools under agreement with the municipality | `results/02_matriculas.csv` |
| `03_gasto_ideb.py` | Spending per student, Ideb and INSE by municipality; regressions with and without the INSE; Ideb by band of spending | `results/03_base_municipios.csv`, `results/03_regressoes.csv`, `results/03_faixas.csv` |
| `08_atualizacao_2025.py` | 2025 checks: lagged INSE, spending and Ideb change by INSE fifth, placebo regressions, samples without implausible scores, median regression, VAAR of 2025, networks with very high Saeb scores | `results/08_*.csv` |
| `09_publica_privada.py` | Public versus private schools in the Saeb 2023, with and without the INSE of the student and of the school | `results/09_*.csv` |
| `13_vaat.py` | VAAT complementation, 2021 to 2025: the 2021 VAAT of every habilitated network, the recipients and amounts of each year, the validation against the official 2021 list, the position relative to the 2021 threshold, the money received and the dose predicted by the formula, and diagnostics that use no outcome data | `results/13_*` |
| `14_poder.py` | Power calculations of the pre-analysis plan, from pre-2019 outcome changes and the dose, without relating them | `results/14_*` |
| `15_siconfi_receitas.py` | Downloads, for every municipality, selected revenues of the DCA (Anexo I-C): current revenue, the ICMS quota, the Union's complementation to the Fundeb and the transfers from the Fundeb | `data/siconfi/receitas_<year>.csv` |
| `16_insumos.py` | School inputs of each municipal network in 2019, 2023 and 2025: creche and pre-school enrollment and full-time shares, full-time share of fundamental, students per class in the early grades, teachers per 100 students (Censo Escolar), share of teachers with higher education and daily class hours (Inep indicators) | `results/16_insumos.csv` |
| `17_participacao_saeb.py` | Saeb participation of the public schools of each municipality, 5th and 9th grades, 2017 and 2023 | `results/17_participacao_saeb.csv` |

Run them in order from `code/` with Python 3 (pandas, numpy, scipy, openpyxl and matplotlib; scripts 08
and 13 also need `pdftotext`, from poppler):

```
python 00_download.py
python 01_siconfi_dca.py 2015 2016 2017 2018 2019 2020 2021 2022 2023 2024 2025
python 15_siconfi_receitas.py 2019 2021
python 16_insumos.py
python 17_participacao_saeb.py
python 02_matriculas.py 2015 2016 2017 2018 2019 2020 2021 2022 2023 2024 2025
python 03_gasto_ideb.py
python 08_atualizacao_2025.py
python 09_publica_privada.py
python 13_vaat.py
python 14_poder.py
```

Scripts 01 and 15 make one API call per municipality and year (about 5,570 calls per year; six to seven
minutes per year with the 12 parallel requests they use) and can be interrupted and resumed. Their extracts
are included in `data/siconfi/`, so the other scripts can be run without them.
Municipalities may correct their DCA after the deadline, so a new download may differ slightly.

## Definitions

- **Spending**: committed expenditure (*despesas empenhadas*) in function 12 (Educação), minus
  subfunction 364 (Ensino Superior), plus subfunction 847 (Transferências para a Educação Básica)
  recorded outside function 12, as described by Todos Pela Educação (2025, p. 4). Subfunction 847
  outside function 12 appears in only three municipalities in 2023. Todos Pela Educação does not say
  whether it excluded anything else (such as pensions of retired staff); nothing else is excluded here.
- **Enrollments**: `QT_MAT_BAS` of municipal schools (`TP_DEPENDENCIA` = 3) in activity, plus
  `QT_MAT_INF` of private schools under agreement (*convênio* or *parceria*) with the municipal
  government, alone or with the state. From 2025 the Censo Escolar puts the enrollment counts in a
  separate table (`Tabela_Matricula`), joined to the school table by school code.
- **Prices**: 2023 reais, deflated by the annual mean of the IPCA (IBGE, table 1737). Todos Pela
  Educação states that it uses the IPCA at 2023 values but not how the index is averaged.
- **Ideb**: observed Ideb of the municipal network (`REDE` = Municipal) in the Inep file released
  in 2026 with the series from 2005 to 2025.
- **INSE**: mean Indicador de Nível Socioeconômico of the municipal network's students (Saeb), all
  locations (`TP_TIPO_REDE` = 3, `TP_LOCALIZACAO` = 0). There is no municipal INSE for 2017; the
  2019 edition is used for 2017 and 2019, and the 2023 edition for 2023 and 2025 (the 2025 edition
  had not been released in November 2026). The 2023 file repeats each
  stratum on several rows; one row per municipality is kept.
- **Samples**: all municipalities with spending, enrollments and an Ideb. A second sample drops the
  1% tails of spending per student, where very small enrollment counts or accounting errors produce
  implausible values; it gives larger coefficients without controls in 2023 (0.081) and the same
  conclusion with the INSE (0.010).
- **VAAR**: complementação da União-VAAR of 2025 made available to each municipality during the year
  (Anexo III of Portaria Interministerial MEC/MF nº 5/2026, column B), divided by the enrollments of
  script 02 and put in 2023 reais.
- **Implausible scores**: municipal networks with a 5th-grade Saeb mathematics mean above 300 in
  2019, 2023 or 2025; the national mean of private schools was 254 in 2025.

## Data

| File | Source |
|---|---|
| `data/siconfi/dca_<year>.csv` | Tesouro Nacional, Siconfi, API de dados abertos, `https://apidatalake.tesouro.gov.br/ords/siconfi/tt/dca` (DCA-Anexo I-E), downloaded in November 2026 |
| `data/siconfi/receitas_<year>.csv` | Tesouro Nacional, Siconfi, same API (DCA-Anexo I-C), 2019 and 2021, downloaded in November 2026 |
| `ibge_municipios.json` | IBGE, API de localidades, municipalities with their immediate geographic regions (2017 division), `https://servicodados.ibge.gov.br/api/v1/localidades/municipios` |
| `pop_2020.json` | IBGE, SIDRA, table 6579 (population estimates, 2020), `https://apisidra.ibge.gov.br/` |
| `microdados_censo_escolar_<year>.zip` | Inep, Microdados do Censo Escolar da Educação Básica, `https://download.inep.gov.br/dados_abertos/` |
| `divulgacao_anos_{iniciais,finais}_municipios_2025.zip` | Inep, Ideb, resultados 2005-2025, `https://download.inep.gov.br/ideb/resultados/` |
| `INSE_2019_MUNICIPIOS.xlsx`, `INSE_2023_municipios.xlsx` | Inep, Indicador de Nível Socioeconômico, `https://download.inep.gov.br/informacoes_estatisticas/indicadores_educacionais/` |
| `ipca_1737.json` | IBGE, SIDRA, table 1737 (IPCA, número-índice), `https://apisidra.ibge.gov.br/` |
| `microdados_saeb_2023.zip` | Inep, Microdados do Saeb 2023 (student files of the 2nd, 5th and 9th grades and of ensino médio), `https://download.inep.gov.br/microdados/` |
| `microdados_saeb_2017.zip` | Inep, Microdados do Saeb 2017 (school file, participation), `https://download.inep.gov.br/microdados/` |
| `indicadores/{DSU,HAD}_<year>_MUNICIPIOS.zip` | Inep, Indicadores Educacionais (percentual de docentes com curso superior; média de horas-aula diária), 2019, 2023 and 2025, `https://download.inep.gov.br/informacoes_estatisticas/indicadores_educacionais/` |
| `divulgacao_brasil_ideb_2025.zip` | Inep, Ideb, resultados 2005-2025 for Brazil by network (national mean of private schools), `https://download.inep.gov.br/ideb/resultados/` |
| `data/fnde/portaria_interministerial_5_2026.pdf` | MEC/MF, Portaria Interministerial nº 5, de 29 de abril de 2026 (Fundeb annual adjustment of 2025, VAAF, VAAT and VAAR by government), FNDE site |
| `data/fnde/vaat/et15_2021.pdf` | Câmara dos Deputados, Consultoria de Orçamento, Estudo Técnico nº 15/2021 (C. R. Tanno, August 2021); its annex gives the 2021 VAAT, revenues and weighted enrollment of every habilitated network |
| `data/fnde/vaat/portaria_10_2021.pdf`, `portaria_6_2022.pdf` | Diário Oficial da União, Portarias Interministeriais nº 10/2021 and nº 6/2022 (Annex III: VAAT complementation by network), FNDE site |
| `data/fnde/vaat/anexo3_portaria_*.pdf` | FNDE, Annex III of the December portarias of 2023 (nº 7), 2024 (nº 13) and 2025 (nº 13) |
| `data/fnde/vaat/acerto_vaat_2023_portaria_7_2026.xlsx`, `ajuste_vaat_2024_portaria_3_2025.xlsx` | FNDE, adjustments of the VAAT complementation of 2023 and 2024 (Annex II) |

SHA-256 checksums of the files used are in `DATA_SHA256SUMS.txt`. The Inep files, the Portarias and the
Câmara study are not included because of their size; the VAAR extracted from the Portaria is in `results/08_vaar_2025.csv`.

**Inep's certificate.** `download.inep.gov.br` does not send the intermediate certificate of its TLS
chain, so command-line downloads fail certificate verification (browsers fetch the missing
certificate on their own). `certs/rnp_icpedu_gr46_ov_tls_ca_2025.pem` is that public intermediate
certificate (RNP ICPEdu GR46 OV TLS CA 2025, issued by GlobalSign Root R46, available at
`http://secure.globalsign.com/cacert/rnpicpedugr46ovtlsca2025.crt`); script 00 adds it to the usual
root certificates and keeps verification on. If the download fails in your environment, download the
files with a browser into `data/inep/`.

## Limits

The descriptive regressions are associations across municipalities, not causal estimates. Since 2023
part of the money follows the indicators (ICMS by education indicators, VAAR), so the association also
runs from results to spending; the placebo regressions of script 08 show it. The INSE measures the
students who took the Saeb, not the whole network. The limits of the causal design are discussed in
the pre-analysis plan.

## License

MIT (code). Data belong to their original publishers and are used under Brazil's open government data
policy (Decreto nº 8.777/2016).
