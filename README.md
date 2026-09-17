[README.md](https://github.com/user-attachments/files/32326195/README.md)
# Employee Attrition Analysis | 员工离职分析

A reproducible portfolio project using 1,470 fictional HR records: data auditing, exploratory analysis, statistical comparisons, and classification with logistic regression and random forest.

基于1,470条公开模拟HR记录，完成数据审计、探索性分析、统计检验与分类模型评估。重点是可靠的分析过程和清晰的业务解释，而不是宣称真实留任效果。

## Key findings / 主要发现

- Overtime employees: 127/416 left (30.53%); no overtime: 110/1,054 (10.44%). Difference: **20.09 percentage points**, 95% CI **15.42–24.99**. This is an association, not a causal effect.
- 加班组与不加班组的样本离职比例相差20.09个百分点；这不能证明减少加班就能带来相同幅度的改善。
- Among employees with 0–1 years at the company, 75/215 left (34.88%). This motivates investigating onboarding, while accounting for the limitations of snapshot data.
- 在公司0–1年的员工离职比例为34.88%，值得调查新人支持，但不能据此估计随时间变化的离职概率。

![Overtime comparison](reports/figures/03_overtime.png)

## Models / 模型结果

Training: 1,176 employees. Test: 294 employees, including 47 leavers. Stratified 80/20 split, seed 42. Five-fold training-only CV selects hyperparameters and model family using average precision (AP). Classification threshold: 0.5.

|Model|Precision|Recall|F1|AP|ROC-AUC|
|---|---:|---:|---:|---:|---:|
|Majority baseline|0.000|0.000|0.000|0.160|0.500|
|Logistic regression|0.773|0.362|0.493|0.678|0.838|
|Random forest|0.625|0.106|0.182|0.438|0.804|

**Logistic regression was selected by training CV, before examining test metrics.** It identified 17 of 47 leavers, missed 30, and falsely flagged 5 non-leavers. Good precision does not imply adequate coverage.

**逻辑回归由训练集交叉验证选定。** 它找出17名离职员工，但漏报30名，因此不能只宣传88.10%的准确率，更不能直接作为人事预警系统。

![Evaluation curves](reports/modeling/evaluation_curves.png)

## Reports / 报告入口

|Topic|中文|English|
|---|---|---|
|Statistics|[统计报告](reports/statistical_report_zh.md)|[Statistical report](reports/statistical_report_en.md)|
|Model evaluation|[模型报告](reports/model_report_zh.md)|[Model report](reports/model_report_en.md)|

Additional materials: [data audit and dictionary](reports/audit_report.md), [EDA](reports/eda_report.md), [modeling protocol](reports/modeling_method.md), and [business follow-up](reports/business_recommendations.md).

早期审计、清洗和EDA报告记录对应阶段的状态；后续统计与建模已经完成。部分验证JSON与员工级输出不会随仓库分发，运行脚本后会重新生成。

## Reproduce / 如何运行

1. Install Python 3.13 and create an isolated environment. Modeling was verified on Python 3.13.5; package versions are in requirements.txt.
2. Download the original dataset using [these instructions](data/raw/README.md). Put the CSV in data/raw. The repository does not redistribute the source data or employee-level processed records.
3. From the repository root, run:

```powershell
python -m venv .venv
# Windows PowerShell; activation is not required:
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe src/audit_clean.py
.venv/Scripts/python.exe src/eda.py
.venv/Scripts/python.exe src/statistical_analysis.py
.venv/Scripts/python.exe src/bilingual_statistics.py
.venv/Scripts/python.exe src/train_models.py
```

On macOS/Linux, replace `.venv/Scripts/python.exe` with `.venv/bin/python`. Chinese EDA charts require an available CJK font (the script tries Microsoft YaHei and SimHei). Modeling charts use English labels.

所有命令在仓库根目录运行。原始CSV只读；中间数据、模型和报告分别生成在data/processed、models和reports中。重跑会覆盖同名生成结果，不能通过反复查看测试成绩来调参。模型文件不随仓库分发，训练脚本会生成两条完整Pipeline。

## Project structure / 目录

```text
src/                    Reproducible Python scripts
data/raw/README.md      Dataset download instructions
reports/                Bilingual reports and aggregate results
reports/figures/        EDA charts
reports/tables/         Aggregate EDA tables
reports/statistics/     Statistical estimates and intervals
reports/modeling/       CV results, test metrics and curves
requirements.txt       Validated modeling environment
```

The upload package excludes dependency directories, caches, raw/processed employee records, saved model binaries, and row-level predictions/split assignments. `.gitignore` keeps those generated items out of subsequent Git commits.

## Validation and limitations / 验证与局限

- Original file hashes and cleaned input hashes were unchanged. Train/test membership is disjoint; preprocessing is fitted within training folds; serialized pipelines reproduce saved predictions.
- Custom statistical formulas were checked against SciPy and statsmodels. Group counts and bilingual report numbers were checked.
- Fictional snapshot data: no known measurement/attrition dates or prospective prediction window. Prior full-sample EDA means this is internal educational evaluation, not untouched external validation.
- No causal retention impact, realized cost savings, calibration or fairness guarantee is claimed. Excluding demographic inputs does not by itself establish fairness.
- 原始数据与处理副本未被修改；测试集仅47个离职样本，单次划分成绩有波动。统计显著性不等于业务措施有效。

Source: [IBM HR Analytics Employee Attrition & Performance dataset page](https://www.kaggle.com/datasets/pavansubhasht/ibm-hr-analytics-attrition-dataset). Follow the publisher's terms when obtaining or redistributing data. No dataset license is granted by this repository.
