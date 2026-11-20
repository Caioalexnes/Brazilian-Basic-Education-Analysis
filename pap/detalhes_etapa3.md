# Stage 3 (spending, school inputs, kink): implementation details

Fixed on 20 November 2026, after Addendum 1 (doi:10.5281/zenodo.24394910) and before any outcome of
this stage is related to the dose, the VAAT position or VAAT receipt. They fill in what the plan leaves
open; where the plan is explicit, it is followed. Section numbers refer to the plan.

## Outcomes

1. **P1, spending per student.** Spending as in script 03 (committed spending in function 12, plus
   subfunction 847 recorded outside function 12, minus subfunction 364), divided by the municipal-network
   enrollment plus the agreement-based early-childhood enrollment (script 02), at 2025 prices (annual
   mean of the IPCA). The outcome is the change from 2019 to 2025. A network without a DCA in either
   year is left out.
2. **S2, spending by stage.** Subfunction 12.365 over early-childhood enrollment (creche and pre-school,
   municipal and agreement-based, script 16), and subfunction 12.361 over municipal fundamental
   enrollment (Censo Escolar, added to script 16). A subfunction absent from the DCA of a municipality
   that reports function 12 counts as zero.
3. **S2, school inputs.** As computed by script 16. Enrollment counts enter as the change in
   ln(1 + enrollment); shares, ratios and hours as changes in levels.
4. **2023 outcomes.** Change from 2019 to 2023, with the dose summed over 2021 to 2023 (Section 5).
5. **Covariates.** A missing INSE 2019 is set to the state mean with a missing-value indicator (Section
   3). The plan does not say what to do with a missing ICMS share; the same rule is used.
6. **Units.** Spending in reais of 2025 per student per year; beta per R$ 1,000 of cumulative predicted
   dose; intervals also shown at the 75th percentile of the positive dose (5.01).

## Inference and multiple testing

7. **P1.** Beta (errors clustered by immediate region) and ATT^o (bootstrap over immediate regions, 999
   draws), reported with equal prominence, with the dose-response curve.
8. **S2.** Benjamini-Hochberg q-values over the p-values of beta for the 14 outcomes (2 spending and 12
   inputs) in 2023 and 2025, 28 tests. ATT^o is reported for each, without q-values.

## Robustness and heterogeneity of P1 (Section 8)

9. Items 1 and 3 to 10 of the robustness list. Item 2 waits for the response to the request to Inep
   (protocol 23546.158945/2026-03); item 11 applies only to event studies.
10. **Dose from the money received.** December portarias plus the adjustments for 2023 (Portaria 7/2026,
    Annex II) and 2024 (Portaria 3/2025, Annex II). The adjustments are in reais and are converted to
    reais per weighted student with the weighted enrollment implied by each year's portaria (total
    complementation over complementation per weighted student).
11. **Heterogeneity.** Interactions of the dose with: the Northeast region; INSE 2019 below the sample
    median; and, among recipients, a mean IEI share over the years received (December portarias) above
    the median. Each regression adds the group indicator.

## Kink (Section 7.6)

12. **Outcome.** [(G2021 + G2022) - (G2018 + G2019)] divided by the enrollment used in the 2021 VAAT
    (annex of the Estudo Técnico 15/2021), where G is spending as in item 1, at 2021 prices. **First
    stage:** the 2021 complementation per weighted student times the ratio of weighted to enrolled
    students, in reais of 2021.
13. **Data check.** The same kink in the Union's complementation recorded as revenue in 2021 (account
    1.7.1.8.09.0.0, Annex I-C; it also includes the VAAF, which is the same per weighted student within a
    state). A missing account counts as zero.
14. **Checks.** Kinks in 2019 spending per student, INSE 2019, ln population 2020 and ICMS share 2019;
    difference in kinks with [(G2018 + G2019) - (G2016 + G2017)] over the same enrollment; placebo
    thresholds at -0.10, -0.05, 0.05 and 0.10 on their own side of the threshold; the permutation test
    (bandwidth 0.2, 200 placebo thresholds); local quadratic; density test at x = 0.
15. **Sample and errors.** The 5,208 networks of the main sample, no covariates, `rdrobust` defaults
    (heteroskedasticity-robust nearest-neighbour variance, no clustering).

## Not pre-specified

16. **Event study of spending per student, 2015 to 2025** (reference 2019; unit and state-by-year
    effects; pre-trend test as in Addendum 1). The plan has no event study for spending. It is reported
    as exploratory, to show the pre-trends behind P1.
