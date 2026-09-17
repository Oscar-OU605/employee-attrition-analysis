"""阶段 1–2：只读原始 CSV，审计并另存保守清洗副本。没有训练模型。"""
from pathlib import Path
import argparse
import hashlib
import io
import json
import platform
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/raw/WA_Fn-UseC_-HR-Employee-Attrition.csv'
# 顺序与原始文件一致；未知单位不自行补全。
FIELDS = [
 ('Age','年龄','数量','岁'),
 ('Attrition','是否离职','目标类别','Yes/No；不是年度离职率'),
 ('BusinessTravel','出差频率','类别','Non-Travel/Travel_Rarely/Travel_Frequently'),
 ('DailyRate','日费率或日薪相关数值','数量','币种与业务口径待确认；不据此推算月收入'),
 ('Department','部门','类别','人力资源、研发、销售'),
 ('DistanceFromHome','家到工作的距离','数量','距离单位待确认'),
 ('Education','教育程度','有序类别','1–5；学历映射待确认'),
 ('EducationField','教育专业领域','类别','专业分类'),
 ('EmployeeCount','员工计数','常量','全部为1'),
 ('EmployeeNumber','员工编号','标识符','仅追踪记录；编号不连续不代表缺失'),
 ('EnvironmentSatisfaction','环境满意度','有序类别','1–4；具体标签待确认'),
 ('Gender','性别','类别','Female/Male；主模型默认排除'),
 ('HourlyRate','小时费率或时薪相关数值','数量','币种与业务口径待确认'),
 ('JobInvolvement','工作投入程度','有序类别','1–4'),
 ('JobLevel','职级','有序类别','1–5'),
 ('JobRole','岗位类型','类别','9类'),
 ('JobSatisfaction','工作满意度','有序类别','1–4'),
 ('MaritalStatus','婚姻状况','类别','主模型默认排除'),
 ('MonthlyIncome','月收入','数量','币种待确认'),
 ('MonthlyRate','月费率相关数值','数量','不等同于MonthlyIncome；口径待确认'),
 ('NumCompaniesWorked','工作过的公司数','数量','0–9；是否包含当前公司待确认'),
 ('Over18','超过18岁的标记','常量','全部为Y；年龄18岁的边界口径待确认'),
 ('OverTime','是否加班','类别','Yes/No；没有加班时数'),
 ('PercentSalaryHike','加薪百分比','数量','11表示11%，原列保持整数百分数'),
 ('PerformanceRating','绩效等级','有序类别','本文件只出现3、4'),
 ('RelationshipSatisfaction','工作关系满意度','有序类别','1–4'),
 ('StandardHours','标准工时','常量','全部为80；统计周期待确认'),
 ('StockOptionLevel','股票期权等级','有序类别','0–3；不是金额'),
 ('TotalWorkingYears','累计工作年数','数量','年'),
 ('TrainingTimesLastYear','上年培训次数','数量','次数；具体年份未知'),
 ('WorkLifeBalance','工作生活平衡','有序类别','1–4'),
 ('YearsAtCompany','在公司年数','数量','年'),
 ('YearsInCurrentRole','当前岗位年数','数量','年'),
 ('YearsSinceLastPromotion','距上次晋升年数','数量','年；0的精确定义待确认'),
 ('YearsWithCurrManager','与当前经理共事年数','数量','年'),
]
EXCLUDE = ['EmployeeNumber','EmployeeCount','Over18','StandardHours','Age','Gender','MaritalStatus']

def digest(data):
    return hashlib.sha256(data).hexdigest()

def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=SOURCE)
    args = parser.parse_args()
    source = args.source.resolve()
    if any(folder == source or folder in source.parents for folder in [ROOT/'data/processed', ROOT/'reports', ROOT/'src']):
        raise ValueError('源文件不能放在生成结果目录中；请使用data/raw或外部路径。')
    original = source.read_bytes()
    df = pd.read_csv(io.BytesIO(original), on_bad_lines='error')
    if list(df.columns) != [f[0] for f in FIELDS]:
        raise ValueError('字段或顺序发生变化，请先更新字段字典。')
    reports = ROOT / 'reports'
    processed = ROOT / 'data' / 'processed'
    for folder in [reports, processed, ROOT/'notebooks', reports/'figures']:
        folder.mkdir(parents=True, exist_ok=True)

    text_cols = [c for c in df if not pd.api.types.is_numeric_dtype(df[c])]
    constants = [c for c in df if df[c].nunique(dropna=False) == 1]
    profile = []
    dictionary = []
    for name, meaning, kind, note in FIELDS:
        s = df[name]
        numeric = pd.api.types.is_numeric_dtype(s)
        profile.append(dict(field=name, storage_type=str(s.dtype), semantic_type=kind,
            missing=int(s.isna().sum()), unique=int(s.nunique()),
            minimum=int(s.min()) if numeric else '', maximum=int(s.max()) if numeric else '',
            blank=int(s.astype('string').str.strip().eq('').sum()),
            surrounding_spaces=int(s.astype('string').ne(s.astype('string').str.strip()).sum()),
            values=json.dumps(sorted(s.dropna().unique().tolist()), ensure_ascii=False) if s.nunique()<=10 else ''))
        dictionary.append(dict(field=name, meaning=meaning, semantic_type=kind, note=note))
    pd.DataFrame(profile).to_csv(reports/'column_profile.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(dictionary).to_csv(reports/'data_dictionary.csv',index=False,encoding='utf-8-sig')

    checks = {
        'company_gt_total': df.YearsAtCompany > df.TotalWorkingYears,
        'role_gt_company': df.YearsInCurrentRole > df.YearsAtCompany,
        'promotion_gt_company': df.YearsSinceLastPromotion > df.YearsAtCompany,
        'manager_gt_company': df.YearsWithCurrManager > df.YearsAtCompany,
        'work_gt_age': df.TotalWorkingYears > df.Age,
        'estimated_start_under_16': df.Age-df.TotalWorkingYears < 16,
    }
    iqr_rows, flags = [], []
    # IQR仅用于数量字段，不用于编号、常量或评分等级。
    for c, _, kind, _ in FIELDS:
        if kind != '数量':
            continue
        q1,q3 = df[c].quantile([.25,.75])
        lower,upper = q1-1.5*(q3-q1), q3+1.5*(q3-q1)
        mask = (df[c]<lower)|(df[c]>upper)
        iqr_rows.append(dict(field=c,q1=q1,q3=q3,lower=lower,upper=upper,flagged=int(mask.sum())))
        for idx in df.index[mask]:
            flags.append(dict(EmployeeNumber=int(df.at[idx,'EmployeeNumber']),field=c,value=int(df.at[idx,c]),reason='1.5xIQR；仅标记，不删除'))
    pd.DataFrame(iqr_rows).to_csv(reports/'outlier_summary.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame(flags,columns=['EmployeeNumber','field','value','reason']).to_csv(reports/'outlier_flags.csv',index=False,encoding='utf-8-sig')
    summary = dict(source=str(source.relative_to(ROOT)) if source.is_relative_to(ROOT) else str(source),source_sha256=digest(original),rows=len(df),columns=len(df.columns),
        numeric_columns=len(df.columns)-len(text_cols),text_columns=len(text_cols),
        missing_cells=int(df.isna().sum().sum()),duplicate_rows=int(df.duplicated().sum()),
        duplicate_rows_without_id=int(df.drop(columns='EmployeeNumber').duplicated().sum()),
        duplicate_ids=int(df.EmployeeNumber.duplicated().sum()),
        blank_cells=sum(p['blank'] for p in profile),surrounding_spaces=sum(p['surrounding_spaces'] for p in profile),
        constants={c:str(df[c].iloc[0]) for c in constants},attrition_counts={str(k):int(v) for k,v in df.Attrition.value_counts().items()},
        attrition_fraction=float(df.Attrition.eq('Yes').mean()),logic_violations={k:int(v.sum()) for k,v in checks.items()},
        unique_employees_flagged=len({f['EmployeeNumber'] for f in flags}),
        python_version=platform.python_version(),pandas_version=pd.__version__)
    save_json(reports/'audit_summary.json',summary)

    # 未知标签不静默转为缺失；出错时保留已生成审计材料，停止导出清洗文件。
    if df.isna().any().any() or df.EmployeeNumber.duplicated().any():
        raise ValueError('检测到缺失值或重复员工编号，需要人工决定处理方法。')
    clean = df.copy(deep=True)
    for c in ['Attrition','OverTime']:
        if not set(df[c].unique()) <= {'Yes','No'}:
            raise ValueError(f'{c}含未知标签，停止清洗。')
        clean[c+'_Flag'] = df[c].map({'Yes':1,'No':0}).astype('int64')
    # 在内存中明确类别语义；CSV不会保存category类型，因此另存schema。
    schema = {name: {'type':kind,'ordered':kind=='有序类别'} for name,_,kind,_ in FIELDS}
    for name,_,kind,_ in FIELDS:
        if kind in ['类别','目标类别','有序类别']:
            clean[name] = pd.Categorical(clean[name],categories=sorted(df[name].unique()),ordered=kind=='有序类别')
            schema[name]['categories'] = sorted(df[name].unique().tolist())
    schema.update({c:dict(type='二元整数',mapping={'No':0,'Yes':1}) for c in ['Attrition_Flag','OverTime_Flag']})
    save_json(processed/'schema.json',schema)
    # 只是记录未来输入约定，不导出训练集，也不拟合转换器或模型。
    feature_contract = dict(target='Attrition_Flag',positive_class=1,
        excluded=EXCLUDE+['Attrition','OverTime'],
        features=[c for c in clean if c not in EXCLUDE+['Attrition','OverTime','Attrition_Flag']],
        note='未来训练前执行划分；原始标签不能作为特征；用OverTime_Flag代替OverTime。')
    save_json(processed/'feature_contract.json',feature_contract)
    target = processed/'employees_clean.csv'
    clean.to_csv(target,index=False,encoding='utf-8-sig')
    restored = pd.read_csv(target)
    pd.testing.assert_frame_equal(restored[df.columns],df)
    assert restored.Attrition_Flag.equals(df.Attrition.map({'Yes':1,'No':0}))
    assert restored.OverTime_Flag.equals(df.OverTime.map({'Yes':1,'No':0}))
    assert digest(source.read_bytes()) == summary['source_sha256'], '原始文件发生变化'
    verification = dict(source_unchanged=True,original_columns_roundtrip_equal=True,
        rows_before=len(df),rows_after=len(restored),columns_before=len(df.columns),columns_after=len(restored.columns),
        source_sha256=summary['source_sha256'],processed_sha256=digest(target.read_bytes()),
        binary_mapping_verified=True,models_trained=False)
    save_json(reports/'verification.json',verification)
    (reports/'cleaning_log.md').write_text('''# 清洗日志（阶段2）

- 原始文件只读，读取前后的SHA-256一致，见verification.json。
- 原35列的值、顺序和全部员工行均保留；CSV重新读取后逐项比较通过。
- 新增Attrition_Flag和OverTime_Flag：Yes=1，No=0。处理后为1470行、37列。
- 未填补缺失值、删除重复行、删除或截断极端值，因为本次没有需要执行这些操作的证据。
- 类别和有序等级在内存中明确类型；CSV不保存类型元数据，schema.json用于后续恢复语义。
- 原始常量和编号保留以便追溯；feature_contract.json记录未来模型的排除项。
- 未来主模型默认排除Age、Gender、MaritalStatus；这不代表模型自动满足公平性要求。
- 未划分训练测试集，未训练模型，未进行探索性分析或统计检验。
''',encoding='utf-8')
    lines=['# 数据审计报告','',
        '本项目使用公开模拟HR数据。每行视为一名员工的快照；没有日期，比例不能称为年度离职率。',
        '',f"来源文件：`{source}`",f"SHA-256：`{summary['source_sha256']}`",'',
        f"数据：{len(df)}行、{len(df.columns)}列；{summary['numeric_columns']}个数值列、{len(text_cols)}个文本列。",
        f"缺失单元格：{summary['missing_cells']}；空字符串：{summary['blank_cells']}；首尾空格：{summary['surrounding_spaces']}。",
        f"重复行：{summary['duplicate_rows']}；去编号后的重复行：{summary['duplicate_rows_without_id']}；重复编号：{summary['duplicate_ids']}。",
        f"离职人数：{summary['attrition_counts'].get('Yes',0)}；样本离职比例：{summary['attrition_fraction']:.2%}。",
        '常量列：'+', '.join(constants)+'。原始副本保留，未来模型排除。','',
        '## 为什么不能直接删除异常值','',
        'IQR是四分位距，即中间50%数据的跨度。超出Q1−1.5×IQR到Q3+1.5×IQR范围只表示数值偏离，不证明录入错误。',
        '例如培训0次或5–6次也会被标记。逐字段标记可重叠，不能相加当作人数。',
        f"共{summary['unique_employees_flagged']}名员工至少在一个数量字段被标记；全部保留。",'',
        '|字段|下界|上界|标记数|','|---|---:|---:|---:|']
    lines += [f"|{r['field']}|{r['lower']:g}|{r['upper']:g}|{r['flagged']}|" for r in iqr_rows]
    lines += ['', '## 逻辑检查','']+[f'- {k}：{v}条。' for k,v in summary['logic_violations'].items()]
    lines += ['', '开始工作年龄是年龄减累计工作年数的近似检查，不是已知入职年龄。所有检查通过不等于数据真实性已得到证明。',
        '', '## 字段字典','', '|字段|含义|语义类型|说明|','|---|---|---|---|']
    lines += ['|'+'|'.join(f)+'|' for f in FIELDS]
    lines += ['', '## 数据局限与待核对事项','',
        '- 来源与字段对应公开IBM模拟数据，不可描述为真实IBM员工调查。',
        '- 无采集时间、离职时间或特征测量时间，无法验证真实未来预测能力或排除时间泄漏。',
        '- 日/时/月费率、币种、距离单位、标准工时周期和部分等级标签待确认。',
        '- 没有干预和成本数据，不能计算已实现的留任收益或推断因果关系。',
        '- 已审阅全样本部分分布，未来模型结果只能表述为教学项目内部评估。',
        '', '[公开数据集说明](https://www.kaggle.com/datasets/pavansubhasht/ibm-hr-analytics-attrition-dataset)',
        '', '下一阶段：经确认后开始探索性分析。本次只完成阶段1–2。']
    (reports/'audit_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(verification,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
