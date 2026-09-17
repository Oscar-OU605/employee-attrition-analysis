# 数据审计报告

本项目使用公开模拟HR数据。每行视为一名员工的快照；没有日期，比例不能称为年度离职率。

来源文件：`data/raw/WA_Fn-UseC_-HR-Employee-Attrition.csv`
SHA-256：`a5c31e38bd7fafc9bc333884eb181b06b41b8e5e488e8f7ccb27199fb3be7659`

数据：1470行、35列；26个数值列、9个文本列。
缺失单元格：0；空字符串：0；首尾空格：0。
重复行：0；去编号后的重复行：0；重复编号：0。
离职人数：237；样本离职比例：16.12%。
常量列：EmployeeCount, Over18, StandardHours。原始副本保留，未来模型排除。

## 为什么不能直接删除异常值

IQR是四分位距，即中间50%数据的跨度。超出Q1−1.5×IQR到Q3+1.5×IQR范围只表示数值偏离，不证明录入错误。
例如培训0次或5–6次也会被标记。逐字段标记可重叠，不能相加当作人数。
共485名员工至少在一个数量字段被标记；全部保留。

|字段|下界|上界|标记数|
|---|---:|---:|---:|
|Age|10.5|62.5|0|
|DailyRate|-573|2195|0|
|DistanceFromHome|-16|32|0|
|HourlyRate|-5.625|137.375|0|
|MonthlyIncome|-5291|16581|114|
|MonthlyRate|-10574.8|39083.2|0|
|NumCompaniesWorked|-3.5|8.5|52|
|PercentSalaryHike|3|27|0|
|TotalWorkingYears|-7.5|28.5|63|
|TrainingTimesLastYear|0.5|4.5|238|
|YearsAtCompany|-6|18|104|
|YearsInCurrentRole|-5.5|14.5|21|
|YearsSinceLastPromotion|-4.5|7.5|107|
|YearsWithCurrManager|-5.5|14.5|14|

## 逻辑检查

- company_gt_total：0条。
- role_gt_company：0条。
- promotion_gt_company：0条。
- manager_gt_company：0条。
- work_gt_age：0条。
- estimated_start_under_16：0条。

开始工作年龄是年龄减累计工作年数的近似检查，不是已知入职年龄。所有检查通过不等于数据真实性已得到证明。

## 字段字典

|字段|含义|语义类型|说明|
|---|---|---|---|
|Age|年龄|数量|岁|
|Attrition|是否离职|目标类别|Yes/No；不是年度离职率|
|BusinessTravel|出差频率|类别|Non-Travel/Travel_Rarely/Travel_Frequently|
|DailyRate|日费率或日薪相关数值|数量|币种与业务口径待确认；不据此推算月收入|
|Department|部门|类别|人力资源、研发、销售|
|DistanceFromHome|家到工作的距离|数量|距离单位待确认|
|Education|教育程度|有序类别|1–5；学历映射待确认|
|EducationField|教育专业领域|类别|专业分类|
|EmployeeCount|员工计数|常量|全部为1|
|EmployeeNumber|员工编号|标识符|仅追踪记录；编号不连续不代表缺失|
|EnvironmentSatisfaction|环境满意度|有序类别|1–4；具体标签待确认|
|Gender|性别|类别|Female/Male；主模型默认排除|
|HourlyRate|小时费率或时薪相关数值|数量|币种与业务口径待确认|
|JobInvolvement|工作投入程度|有序类别|1–4|
|JobLevel|职级|有序类别|1–5|
|JobRole|岗位类型|类别|9类|
|JobSatisfaction|工作满意度|有序类别|1–4|
|MaritalStatus|婚姻状况|类别|主模型默认排除|
|MonthlyIncome|月收入|数量|币种待确认|
|MonthlyRate|月费率相关数值|数量|不等同于MonthlyIncome；口径待确认|
|NumCompaniesWorked|工作过的公司数|数量|0–9；是否包含当前公司待确认|
|Over18|超过18岁的标记|常量|全部为Y；年龄18岁的边界口径待确认|
|OverTime|是否加班|类别|Yes/No；没有加班时数|
|PercentSalaryHike|加薪百分比|数量|11表示11%，原列保持整数百分数|
|PerformanceRating|绩效等级|有序类别|本文件只出现3、4|
|RelationshipSatisfaction|工作关系满意度|有序类别|1–4|
|StandardHours|标准工时|常量|全部为80；统计周期待确认|
|StockOptionLevel|股票期权等级|有序类别|0–3；不是金额|
|TotalWorkingYears|累计工作年数|数量|年|
|TrainingTimesLastYear|上年培训次数|数量|次数；具体年份未知|
|WorkLifeBalance|工作生活平衡|有序类别|1–4|
|YearsAtCompany|在公司年数|数量|年|
|YearsInCurrentRole|当前岗位年数|数量|年|
|YearsSinceLastPromotion|距上次晋升年数|数量|年；0的精确定义待确认|
|YearsWithCurrManager|与当前经理共事年数|数量|年|

## 数据局限与待核对事项

- 来源与字段对应公开IBM模拟数据，不可描述为真实IBM员工调查。
- 无采集时间、离职时间或特征测量时间，无法验证真实未来预测能力或排除时间泄漏。
- 日/时/月费率、币种、距离单位、标准工时周期和部分等级标签待确认。
- 没有干预和成本数据，不能计算已实现的留任收益或推断因果关系。
- 已审阅全样本部分分布，未来模型结果只能表述为教学项目内部评估。

[公开数据集说明](https://www.kaggle.com/datasets/pavansubhasht/ibm-hr-analytics-attrition-dataset)

下一阶段：经确认后开始探索性分析。此报告记录阶段1–2；后续分析和建模已经完成，见README。
