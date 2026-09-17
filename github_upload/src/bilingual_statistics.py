"""从同一统计结果生成独立的英文报告与中文副本，避免手工抄错数字。"""
from pathlib import Path
import json
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]

def main():
    folder=ROOT/'reports'
    data=json.loads((folder/'statistics/results.json').read_text(encoding='utf-8'))
    overall=data['overall']; primary=data['primary_test']
    def table(rows):
        lines=['|Group|Overtime: leavers / employees|No overtime: leavers / employees|Difference (pp)|95% CI (pp)|Caution|','|---|---:|---:|---:|---|---|']
        for r in rows:
            note=[]
            if r['small_sample']:note.append('At least one group n<30')
            if r['sparse_expected']:note.append('Expected count<5')
            lines.append(f"|{r['group']}|{r['overtime_leavers']}/{r['overtime_n']} ({r['overtime_rate']:.2%})|{r['no_overtime_leavers']}/{r['no_overtime_n']} ({r['no_overtime_rate']:.2%})|{100*r['difference']:.2f}|[{100*r['ci_low']:.2f}, {100*r['ci_high']:.2f}]|{'; '.join(note)}|")
        return '\n'.join(lines)
    o=dict(overall,group='All employees')
    lines=['# Overtime and employee attrition: statistical report (Stage 5)','',
        'This analysis uses 1,470 fictional HR records. Statistical inference is an educational demonstration: the sampling design, independence of employees and timing of measurements cannot be verified. Results are not causal evidence for a real employer. Model training is a separate stage; this report covers statistical analysis only.',
        '', '## Effect size and uncertainty','',table([o]),'',
        f"The overtime group has a sample attrition proportion **{100*o['difference']:.2f} percentage points higher** than the no-overtime group. The 95% confidence interval is **{100*o['ci_low']:.2f} to {100*o['ci_high']:.2f} percentage points**, excluding zero.",
        'Percentage points are the arithmetic difference between percentages, not relative percentage growth or an estimate of the benefit of reducing overtime.',
        'Under independent sampling and the other assumptions, about 95% of intervals produced by this method over repeated samples would cover the true difference. This does not assign a 95% probability to the true difference lying within this particular interval, and it says nothing about causation.',
        '', '## What does the chi-square test ask?','',
        'The null hypothesis is that overtime status and attrition are independent. We use the Pearson chi-square test of association with one degree of freedom and no Yates continuity correction.',
        f"Chi-square = {primary['chi_square']:.6f}; p = {primary['p_value']:.6g}; minimum expected cell count = {primary['minimum_expected']:.2f} (all at least 5).",
        'Expected counts are the counts implied by independence, not the observed counts. The overall table meets the usual large-sample expected-count rule.',
        'The p-value is the probability of a statistic at least as extreme as observed if the null hypothesis and model assumptions hold. It is neither the probability that the null is true nor the probability that overtime causes attrition.',
        '', '## Stratification by job role','',table(pd.read_csv(folder/'statistics/JobRole_differences.csv').to_dict('records')),'',
        'Eight of nine roles have positive observed differences; Healthcare Representative has a negative difference. This does not establish a common effect in every role. Wide intervals or intervals crossing zero can reflect limited precision; crossing zero does not prove absence of association.',
        '', '## Stratification by job level','',table(pd.read_csv(folder/'statistics/JobLevel_differences.csv').to_dict('records')),'',
        'All five levels have positive observed differences, but attrition counts are small at senior levels. A significant result in one group and a non-significant result in another do not establish a significant difference between their effects; that requires an interaction analysis.',
        '', '## Overall association after stratification: exploratory supplements','']
    for key,r in data['exploratory_cmh'].items():
        lines.append(f"- Stratified by {key}: CMH chi-square = {r['chi_square']:.4f}, p = {r['p_value']:.6g}; {r['strata']} strata, of which {r['sparse_strata']} have an expected cell count below 5.")
    lines+=['',
        'The Cochran–Mantel–Haenszel (CMH) test combines within-stratum evidence. Role and level are considered separately, not jointly; other confounders remain unaccounted for. The aggregate association persists under these separate stratifications. Sparse strata require caution with asymptotic p-values. We do not claim equal effects across strata or report one universal causal effect.',
        'The subgroup intervals are pointwise, unadjusted 95% intervals, not simultaneous confidence intervals. No subgroup significance ranking or smallest-p-value selection is performed. The CMH supplements are exploratory, not additional confirmatory discoveries.',
        '', '## Methods and reproducibility','',
        '- Input: the cleaned copy. Employees are treated as independent units; overtime groups do not overlap. No outliers or small strata are removed.',
        '- Wilson intervals for individual proportions; Newcombe intervals for differences between independent proportions.',
        '- The statistics script implements published formulas using the Python standard library and pandas; it does not require SciPy or statsmodels. Checks cover equivalence to the two-proportion z statistic, reversed group order, zero/all-success boundaries and a known chi-square tail probability.',
        '- The association was already inspected during EDA. This remains exploratory, not a preregistered independent confirmation.',
        '- Source and cleaned-file hash checks are recorded in statistics/verification.json. CSV intervals are on the 0–1 scale; this report multiplies by 100 to display percentage points.',
        '', 'References: [Newcombe intervals](https://www.statsmodels.org/stable/generated/statsmodels.stats.proportion.confint_proportions_2indep.html), [interval implementation](https://www.statsmodels.org/stable/_modules/statsmodels/stats/proportion.html), [CMH implementation](https://www.statsmodels.org/stable/_modules/statsmodels/stats/contingency_tables.html).',
        '', '## Business interpretation','',
        'Investigate workload, scheduling, role expectations and management support in overtime-heavy roles. Reducing overtime is not yet a validated retention intervention. Time-stamped longitudinal data and a prospectively designed intervention evaluation would be needed to estimate its effect.',
        'Prediction is a separate question: statistical association does not establish predictive performance. See the separate modeling reports for the subsequent training and evaluation stage.']
    (folder/'statistical_report_en.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    zh=(folder/'statistical_report.md').read_text(encoding='utf-8').replace('未训练模型。','本报告仅讨论统计分析；模型训练结果另见模型报告。').replace('SciPy和statsmodels未安装，本脚本用标准库实现公开公式，不新增依赖；','统计脚本用标准库实现公开公式，不依赖SciPy或statsmodels；').replace('下一阶段可进入分类模型扩展，但统计关联不等于预测能力；暂未划分训练测试集，也未建模。','统计关联不等于预测能力；后续模型训练和评估单独记录在模型报告。')
    (folder/'statistical_report_zh.md').write_text(zh,encoding='utf-8')
    (folder/'statistical_report.md').write_text(zh,encoding='utf-8')
    print('Created statistical_report_zh.md and statistical_report_en.md from shared statistics.')

if __name__=='__main__':main()
