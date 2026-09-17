# Overtime and employee attrition: statistical report (Stage 5)

This analysis uses 1,470 fictional HR records. Statistical inference is an educational demonstration: the sampling design, independence of employees and timing of measurements cannot be verified. Results are not causal evidence for a real employer. Model training is a separate stage; this report covers statistical analysis only.

## Effect size and uncertainty

|Group|Overtime: leavers / employees|No overtime: leavers / employees|Difference (pp)|95% CI (pp)|Caution|
|---|---:|---:|---:|---|---|
|All employees|127/416 (30.53%)|110/1054 (10.44%)|20.09|[15.42, 24.99]||

The overtime group has a sample attrition proportion **20.09 percentage points higher** than the no-overtime group. The 95% confidence interval is **15.42 to 24.99 percentage points**, excluding zero.
Percentage points are the arithmetic difference between percentages, not relative percentage growth or an estimate of the benefit of reducing overtime.
Under independent sampling and the other assumptions, about 95% of intervals produced by this method over repeated samples would cover the true difference. This does not assign a 95% probability to the true difference lying within this particular interval, and it says nothing about causation.

## What does the chi-square test ask?

The null hypothesis is that overtime status and attrition are independent. We use the Pearson chi-square test of association with one degree of freedom and no Yates continuity correction.
Chi-square = 89.043879; p = 3.86152e-21; minimum expected cell count = 67.07 (all at least 5).
Expected counts are the counts implied by independence, not the observed counts. The overall table meets the usual large-sample expected-count rule.
The p-value is the probability of a statistic at least as extreme as observed if the null hypothesis and model assumptions hold. It is neither the probability that the null is true nor the probability that overtime causes attrition.

## Stratification by job role

|Group|Overtime: leavers / employees|No overtime: leavers / employees|Difference (pp)|95% CI (pp)|Caution|
|---|---:|---:|---:|---|---|
|Healthcare Representative|2/37 (5.41%)|7/94 (7.45%)|-2.04|[-10.18, 10.83]|Expected count<5|
|Human Resources|5/13 (38.46%)|7/39 (17.95%)|20.51|[-4.93, 48.03]|At least one group n<30; Expected count<5|
|Laboratory Technician|31/62 (50.00%)|31/197 (15.74%)|34.26|[20.89, 47.13]||
|Manager|4/27 (14.81%)|1/75 (1.33%)|13.48|[2.84, 31.18]|At least one group n<30; Expected count<5|
|Manufacturing Director|4/39 (10.26%)|6/106 (5.66%)|4.60|[-4.13, 18.26]|Expected count<5|
|Research Director|1/23 (4.35%)|1/57 (1.75%)|2.59|[-5.75, 19.30]|At least one group n<30; Expected count<5|
|Research Scientist|33/97 (34.02%)|14/195 (7.18%)|26.84|[17.08, 37.12]||
|Sales Executive|31/94 (32.98%)|26/232 (11.21%)|21.77|[11.91, 32.36]||
|Sales Representative|16/24 (66.67%)|17/59 (28.81%)|37.85|[14.27, 56.17]|At least one group n<30|

Eight of nine roles have positive observed differences; Healthcare Representative has a negative difference. This does not establish a common effect in every role. Wide intervals or intervals crossing zero can reflect limited precision; crossing zero does not prove absence of association.

## Stratification by job level

|Group|Overtime: leavers / employees|No overtime: leavers / employees|Difference (pp)|95% CI (pp)|Caution|
|---|---:|---:|---:|---|---|
|1|82/156 (52.56%)|61/387 (15.76%)|36.80|[28.05, 45.16]||
|2|26/146 (17.81%)|26/388 (6.70%)|11.11|[5.00, 18.42]||
|3|13/63 (20.63%)|19/155 (12.26%)|8.38|[-1.81, 20.68]||
|4|3/33 (9.09%)|2/73 (2.74%)|6.35|[-2.62, 20.97]|Expected count<5|
|5|3/18 (16.67%)|2/51 (3.92%)|12.75|[-1.53, 35.48]|At least one group n<30; Expected count<5|

All five levels have positive observed differences, but attrition counts are small at senior levels. A significant result in one group and a non-significant result in another do not establish a significant difference between their effects; that requires an interaction analysis.

## Overall association after stratification: exploratory supplements

- Stratified by JobRole: CMH chi-square = 96.4425, p = 9.1875e-23; 9 strata, of which 5 have an expected cell count below 5.
- Stratified by JobLevel: CMH chi-square = 92.1769, p = 7.92646e-22; 5 strata, of which 2 have an expected cell count below 5.

The Cochran–Mantel–Haenszel (CMH) test combines within-stratum evidence. Role and level are considered separately, not jointly; other confounders remain unaccounted for. The aggregate association persists under these separate stratifications. Sparse strata require caution with asymptotic p-values. We do not claim equal effects across strata or report one universal causal effect.
The subgroup intervals are pointwise, unadjusted 95% intervals, not simultaneous confidence intervals. No subgroup significance ranking or smallest-p-value selection is performed. The CMH supplements are exploratory, not additional confirmatory discoveries.

## Methods and reproducibility

- Input: the cleaned copy. Employees are treated as independent units; overtime groups do not overlap. No outliers or small strata are removed.
- Wilson intervals for individual proportions; Newcombe intervals for differences between independent proportions.
- The statistics script implements published formulas using the Python standard library and pandas; it does not require SciPy or statsmodels. Checks cover equivalence to the two-proportion z statistic, reversed group order, zero/all-success boundaries and a known chi-square tail probability.
- The association was already inspected during EDA. This remains exploratory, not a preregistered independent confirmation.
- Source and cleaned-file hash checks are recorded in statistics/verification.json. CSV intervals are on the 0–1 scale; this report multiplies by 100 to display percentage points.

References: [Newcombe intervals](https://www.statsmodels.org/stable/generated/statsmodels.stats.proportion.confint_proportions_2indep.html), [interval implementation](https://www.statsmodels.org/stable/_modules/statsmodels/stats/proportion.html), [CMH implementation](https://www.statsmodels.org/stable/_modules/statsmodels/stats/contingency_tables.html).

## Business interpretation

Investigate workload, scheduling, role expectations and management support in overtime-heavy roles. Reducing overtime is not yet a validated retention intervention. Time-stamped longitudinal data and a prospectively designed intervention evaluation would be needed to estimate its effect.
Prediction is a separate question: statistical association does not establish predictive performance. See the separate modeling reports for the subsequent training and evaluation stage.
