# 建模方案 / Modeling protocol

此方案在读取测试成绩前固定。The protocol is fixed before test evaluation.

- 数据 / Data: employees_clean.csv；以Attrition_Flag=1为离职。
- 划分 / Split: stratified 80/20, random_state=42。训练集内StratifiedKFold(5, shuffle=True, random_state=42)。
- 输入 / Inputs: feature_contract.json中27个字段；不使用原始目标、编号、常量、年龄、性别、婚姻状况。
- 编码 / Encoding: nominal and rating fields use one-hot encoding; unknown categories ignored. 评分独热编码，不假定相邻等级间距相等。
- 逻辑回归 / Logistic regression: lbfgs, max_iter=3000; C∈{0.1,1,10}; class_weight∈{None,balanced}；其他数值字段标准化。
- 随机森林 / Random forest: 300 trees, max_depth∈{5,None}, min_samples_leaf∈{1,5}, class_weight∈{None,balanced}, random_state=42。数值不标准化。
- 选择 / Selection: maximize training five-fold mean average precision (AP); ties favor logistic regression. 参数和模型均只由训练集决定。
- 阈值 / Threshold: 0.5，固定；不使用测试结果选择阈值。
- 基准 / Baseline: DummyClassifier(strategy=most_frequent)，预测全部不离职。
- 输出 / Outputs: CV search tables, fixed split assignments, final test metrics and predictions, serialized pipelines, bilingual reports.
- 测试 / Verification: split disjointness, target exclusion, train-only scaler means, confusion matrix totals, serialization parity, source and cleaned-file hashes.

所有模型使用相同的训练/测试划分和交叉验证折。All models share the same split and CV folds. No SMOTE, no automatic outlier removal, no test-driven retuning. 测试集只用作最终评估；保存后的预测可以用于核对指标，不重新训练或筛选模型。

由于已经探索全样本、没有时间字段、数据为模拟样本，结果属于内部教学评估。Because the full dataset was previously explored and dates are unavailable, results do not establish external or prospective validity.
