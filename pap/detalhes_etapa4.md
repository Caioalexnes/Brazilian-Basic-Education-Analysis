# Stage 4 (learning): implementation details

Fixed on 20 November 2026, after the results of stage 3 (commits 5469a94 and 242bf07) and before any
learning outcome is related to the dose, the VAAT position or VAAT receipt. They fill in what the plan
leaves open; where the plan or Addendum 1 is explicit, it is followed. Section numbers refer to the plan.

## Outcomes

1. **P2.** Change from 2019 to 2025 in the standardized Saeb mean N (`VL_NOTA_MEDIA`) of the municipal
   network, 5th and 9th grades, from Inep's Ideb files by municipality (2025 release). A network enters
   if N is observed in 2019 and 2025. Holm correction across the two grades.
2. **Units.** Beta in points of N (0 to 10) per R$ 1,000 of cumulative predicted dose; intervals also at
   the 75th percentile of the positive dose (5.01) and in student standard deviations. N is the mean of
   mathematics and Portuguese, each rescaled as 10 (S - S_inf) / (S_sup - S_inf), with Inep's limits
   (5th grade: mathematics 60 to 322, Portuguese 49 to 324; 9th grade: 100 to 400 in both; Inep, Nota
   Técnica nº 1, Table 2). If the effect is d student standard deviations in both subjects,
   change in N = 5 d (SD_mat / range_mat + SD_por / range_por). With the student standard deviations of
   public schools in the Saeb 2023 (script 09: 53.4 and 52.4 in the 5th grade, 53.1 and 51.5 in the 9th),
   one point of N is 0.507 student SD in the 5th grade and 0.574 in the 9th.
3. **S1 (13 tests, Benjamini-Hochberg within the family).** Change from 2019 to 2025 in the Ideb, the
   mathematics score, the Portuguese score and the flow indicator P, 5th and 9th grades (8 tests); N
   from 2019 to 2023, with the dose summed up to 2023 (2 tests); the Saeb participation rate of the
   public schools of the municipality, from 2017 to 2023, with the dose summed up to 2023, 5th and 9th
   grades (2 tests; the 2019 school files are anonymized and the 2025 files are not released); the
   change in the INSE of the municipal network from 2019 to 2023, with the dose summed up to 2023
   (1 test). Mathematics and Portuguese are also expressed in student standard deviations.
4. **Covariates and sample.** As in stage 3 (item 5 of `detalhes_etapa3.md`): the 5,208 networks of the
   main sample, the INSE 2019, ln population 2020 and ICMS share 2019, missing values set to the state
   mean with an indicator, errors clustered by immediate region. P2 reports beta and ATT^o (bootstrap
   over immediate regions, 999 draws) with equal prominence, with the dose-response curve.

## Event study and sensitivity

5. **Event study** of N, 5th and 9th grades, every Ideb round from 2005 to 2025, reference 2019,
   unbalanced panel. Pre-trend test on 2005 to 2017 with the wild cluster bootstrap p-value
   (Addendum 1); the 2021 coefficient is reported and not interpreted. Balanced panel (networks with N
   in all 11 rounds) as robustness check 11.
6. **HonestDiD** relative-magnitudes bounds on the 2025 coefficient of each grade, Mbar of 0.5, 1, 1.5
   and 2, breakdown value by bisection to within 0.05, shown next to the simulated benchmark of
   Addendum 1. **Linear trend** fitted to the 2009 to 2017 coefficients and extrapolated to 2025.

## Within-municipality comparison (Section 7.4)

7. Municipalities with N of both the municipal and the state network in 2019 and 2025. Outcome: the
   change in N of the municipal network minus that of the state network; negative control: the change
   in N of the state network. Same covariates as item 4.

## Robustness and heterogeneity of P2 (Section 8)

8. Items 1, 3 to 10 and 11 of the robustness list, as implemented in stage 3 (items 9 and 10 of
   `detalhes_etapa3.md`); item 2 waits for the response to the request to Inep (protocol
   23546.158945/2026-03). Weighting (item 9) uses the 2019 enrollment of the municipal network, as in
   stage 3. Heterogeneity as in item 11 of `detalhes_etapa3.md`.
9. **Interpretation.** The rules of Section 10 as amended by Addendum 1: if the pre-trend test rejects
   (wild bootstrap p < 0.05) or the negative control is significant, the learning results are presented
   as not robust to plausible violations of parallel trends.

## Declared risk

10. Script 25 (exploratory, enrollment only) shows that high-dose municipalities had continuing
    municipalization of fundamental schooling and rising total enrollment, before and after 2019.
    Students who move from state to municipal schools change the composition of both networks. This can
    bias the main estimate, the within-municipality comparison and the negative control, in either
    direction. The composition outcomes of the plan (participation and INSE) are reported with the
    learning results, and the event study of the state share of public fundamental enrollment
    (script 25) is shown next to them as exploratory. The specification of the plan is not changed.

## Where it runs

11. Script 26 runs everything except HonestDiD and saves the event-study coefficients and their
    covariance; script 27 runs HonestDiD (needs R).
