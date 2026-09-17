"""阶段5：加班与离职的探索性统计。只读输入，不训练模型。

采用Python标准库实现Wilson/Newcombe、Pearson卡方与CMH公式；
公式出处见报告。无需安装SciPy或statsmodels。
"""
from pathlib import Path
from math import sqrt, erfc, isclose
from statistics import NormalDist
import hashlib
import json
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def wilson(x, n):
    if n <= 0 or not 0 <= x <= n:
        raise ValueError('人数必须为正，离职数必须介于0和人数之间。')
    p=x/n
    z=NormalDist().inv_cdf(.975)
    denominator=1+z*z/n
    center=(p+z*z/(2*n))/denominator
    half=z*sqrt(p*(1-p)/n+z*z/(4*n*n))/denominator
    return max(0.,center-half),min(1.,center+half)

def newcombe(x1,n1,x0,n0):
    """两独立比例之差的95% Newcombe区间，基于Wilson区间。"""
    p1,p0=x1/n1,x0/n0
    l1,u1=wilson(x1,n1)
    l0,u0=wilson(x0,n0)
    diff=p1-p0
    return diff-sqrt((p1-l1)**2+(u0-p0)**2),diff+sqrt((u1-p1)**2+(p0-l0)**2)

def pearson(a,b,c,d):
    """表格为[[加班离职,加班未离职],[不加班离职,不加班未离职]]。"""
    total=a+b+c+d
    expected=[(a+b)*(a+c)/total,(a+b)*(b+d)/total,(c+d)*(a+c)/total,(c+d)*(b+d)/total]
    if min(expected)<=0:
        raise ValueError('边际计数为0，不能使用此卡方检验。')
    stat=sum((obs-exp)**2/exp for obs,exp in zip([a,b,c,d],expected))
    # 自由度1的卡方右尾概率，避免1-CDF导致极小p值变成0。
    return stat,erfc(sqrt(stat/2)),expected

def contrast(frame, label):
    yes=frame.loc[frame.OverTime=='Yes','Attrition_Flag']
    no=frame.loc[frame.OverTime=='No','Attrition_Flag']
    a,n1,c,n0=int(yes.sum()),len(yes),int(no.sum()),len(no)
    if not n1 or not n0:
        raise ValueError(f'{label}缺少一个加班组，不能比较。')
    lo,hi=newcombe(a,n1,c,n0)
    stat,p,expected=pearson(a,n1-a,c,n0-c)
    l1,u1=wilson(a,n1);l0,u0=wilson(c,n0)
    return dict(group=str(label),overtime_n=n1,overtime_leavers=a,overtime_rate=a/n1,
        overtime_ci_low=l1,overtime_ci_high=u1,no_overtime_n=n0,no_overtime_leavers=c,
        no_overtime_rate=c/n0,no_overtime_ci_low=l0,no_overtime_ci_high=u0,
        difference=a/n1-c/n0,ci_low=lo,ci_high=hi,minimum_expected=min(expected),
        sparse_expected=min(expected)<5,small_sample=min(n1,n0)<30), (stat,p,expected)

def cmh(rows):
    """探索性CMH检验，分别按一个变量分层；无连续性校正。"""
    numerator=variance=0.
    for r in rows:
        a,c=r['overtime_leavers'],r['no_overtime_leavers']
        n1,n0=r['overtime_n'],r['no_overtime_n']
        n=n1+n0
        numerator += a-n1*(a+c)/n
        variance += n1*n0*(a+c)*(n-a-c)/(n*n*(n-1))
    if variance<=0:
        raise ValueError('CMH方差为0，无法检验。')
    stat=numerator*numerator/variance
    return dict(chi_square=stat,df=1,p_value=erfc(sqrt(stat/2)),continuity_correction=False,
        strata=len(rows),sparse_strata=sum(r['sparse_expected'] for r in rows))

def checks():
    # 边界、组别交换以及已知卡方尾概率：保护统计公式的关键性质。
    assert isclose(wilson(0,10)[0],0,abs_tol=1e-12)
    assert isclose(wilson(10,10)[1],1,abs_tol=1e-12)
    lo,hi=newcombe(0,10,10,10)
    assert -1<=lo<=hi<=0
    lo,hi=newcombe(127,416,110,1054)
    revlo,revhi=newcombe(110,1054,127,416)
    assert isclose(lo,-revhi) and isclose(hi,-revlo)
    assert isclose(erfc(sqrt(3.841458820694124/2)),.05,rel_tol=1e-10)
    stat,p,_=pearson(10,10,10,10)
    assert stat==0 and p==1
    stat,_,_=pearson(127,289,110,944)
    pooled=237/1470
    z=(127/416-110/1054)/sqrt(pooled*(1-pooled)*(1/416+1/1054))
    assert isclose(stat,z*z,rel_tol=1e-12)

def main():
    checks()
    inp=ROOT/'data/processed/employees_clean.csv'
    before=sha(inp)
    audit=json.loads((ROOT/'reports/audit_summary.json').read_text(encoding='utf-8'))
    source=ROOT / audit['source']
    assert sha(source)==audit['source_sha256']
    d=pd.read_csv(inp)
    assert not d.EmployeeNumber.duplicated().any()
    assert set(d.OverTime)=={'Yes','No'}
    assert d.Attrition_Flag.equals(d.Attrition.map({'Yes':1,'No':0}))
    out=ROOT/'reports/statistics'
    out.mkdir(exist_ok=True)
    overall,(stat,p,expected)=contrast(d,'全部员工')
    assert min(expected)>=5, '总体期望计数不足，不应使用当前Pearson近似'
    pd.DataFrame([overall]).to_csv(out/'overall_difference.csv',index=False,encoding='utf-8-sig')
    observed=[[overall['overtime_leavers'],overall['overtime_n']-overall['overtime_leavers']],
              [overall['no_overtime_leavers'],overall['no_overtime_n']-overall['no_overtime_leavers']]]
    pd.DataFrame(observed,index=['OverTime_Yes','OverTime_No'],columns=['Attrition_Yes','Attrition_No']).to_csv(out/'observed_counts.csv',encoding='utf-8-sig')
    summaries={}
    stratified={}
    for col in ['JobRole','JobLevel']:
        rows=[contrast(g,k)[0] for k,g in d.groupby(col)]
        assert sum(r['overtime_n']+r['no_overtime_n'] for r in rows)==len(d)
        assert sum(r['overtime_leavers']+r['no_overtime_leavers'] for r in rows)==int(d.Attrition_Flag.sum())
        pd.DataFrame(rows).to_csv(out/(col+'_differences.csv'),index=False,encoding='utf-8-sig')
        stratified[col]=rows
        summaries[col]=cmh(rows)
    result=dict(primary_test=dict(method='Pearson chi-square, no continuity correction',chi_square=stat,
        df=1,p_value=p,expected_counts=[expected[:2],expected[2:]],minimum_expected=min(expected)),
        overall=overall,exploratory_cmh=summaries,confidence_method='95% Newcombe difference from Wilson intervals',
        subgroup_intervals='pointwise, unadjusted; not simultaneous confidence intervals',models_trained=False)
    (out/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    def table(rows):
        lines=['|分组|加班：离职/人数|不加班：离职/人数|差值（百分点）|95%区间（百分点）|提示|','|---|---:|---:|---:|---|---|']
        for r in rows:
            notes=[]
            if r['small_sample']:notes.append('至少一组<30人')
            if r['sparse_expected']:notes.append('期望计数<5')
            lines.append(f"|{r['group']}|{r['overtime_leavers']}/{r['overtime_n']} ({r['overtime_rate']:.2%})|{r['no_overtime_leavers']}/{r['no_overtime_n']} ({r['no_overtime_rate']:.2%})|{r['difference']*100:.2f}|[{r['ci_low']*100:.2f}, {r['ci_high']*100:.2f}]|{'；'.join(notes)}|")
        return '\n'.join(lines)
    lines=['# 加班与离职：统计分析报告（阶段5）','',
        '本报告使用1470条公开模拟HR记录。统计推断是方法演示：真实抽样方式、员工间独立性和测量时间均无法确认，结论不能外推为真实企业的因果规律。未训练模型。','',
        '## 先看差多少，再看不确定性','',table([overall]),'',
        f"加班组的样本离职比例高出 **{overall['difference']*100:.2f}个百分点**。95%置信区间为 **{overall['ci_low']*100:.2f}至{overall['ci_high']*100:.2f}个百分点**，未包含0。",
        '百分点是两个百分比直接相减；它不是相对增长百分比，也不是减少加班后预计能减少的离职人数。',
        '95%置信区间的含义：在独立抽样等假设成立、重复抽样并使用相同方法时，约95%的区间会覆盖真实比例差。它不是“真实差值有95%的概率位于这个已算出的区间”，更不说明因果关系。','',
        '## 卡方检验在问什么','',
        '零假设：加班状态与离职标签无关联。使用双侧关联检验、自由度1的Pearson卡方统计量，不使用Yates连续性校正。',
        f'统计量 χ²={stat:.6f}，p={p:.6g}，最小期望计数={min(expected):.2f}（全部≥5）。',
        '期望计数是假设两者无关联时预计出现在各单元格的人数，不是实际人数。总体计数满足常见的卡方大样本近似要求。',
        'p值表示：若零假设和模型假设成立，观察到当前或更极端统计量的概率。它不是“无关联成立的概率”，也不是“加班导致离职的概率”。本例提供关联证据，不提供因果证据。','',
        '## 按岗位看：方向是否一致','',table(stratified['JobRole']),'',
        '9个岗位中8个观察差值为正；Healthcare Representative为负。不能宣称每个岗位都同样受影响。区间较宽、跨0的组可能缺乏精度；跨0不等于证明没有关联。',
        '', '## 按职级看','',table(stratified['JobLevel']),'',
        '5个职级的观察差值均为正，但高职级离职人数很少，区间较宽。不能用“某组显著、另一组不显著”推断两组效应存在显著差异；这需要另行检验交互作用。','',
        '## 分层后的整体关联（探索性补充）','']
    for col,res in summaries.items():
        lines.append(f"- 按{col}分别分层：CMH χ²={res['chi_square']:.4f}，p={res['p_value']:.6g}；{res['strata']}层，其中{res['sparse_strata']}层存在期望计数<5。")
    lines += ['','CMH在每层内比较加班与离职的关联，再合并检验信息。这里分别按岗位、按职级进行，不是同时控制两者，更没有控制全部混杂因素。结果说明整体关联没有仅因这两种单变量分层而消失。稀疏层存在，渐近p值应谨慎解释；不把结果说成每层效应相同，也不报告一个适用于所有员工的统一效果。',
        '岗位和职级分析是探索性补充；每层区间是未做多重比较调整的单独95%区间，不保证整张表同时有95%覆盖率。不逐层做显著性排名、不筛选最小p值；CMH补充检验也不作为新的确认性发现。',
        '', '## 方法与可复现说明','',
        '- 输入是清洗副本；员工视为独立单位，两个加班组互斥。未删除极端值或小组。',
        '- 单比例区间使用Wilson方法；比例差采用Newcombe方法，避免简单Wald区间在小计数时表现不佳。',
        '- SciPy和statsmodels未安装，本脚本用标准库实现公开公式，不新增依赖；对照两比例z检验与卡方统计量等价关系、交换组别、0/全成功边界及已知尾概率做校验。',
        '- 该主题在EDA中已经被看到，因此仍属于探索性分析，不是预注册的独立确认试验。',
        '- 原始文件、清洗副本哈希核对结果见verification.json；输出CSV以0–1比例保存区间，报告乘100展示百分点。',
        '', '公式参考：[Newcombe区间文档](https://www.statsmodels.org/stable/generated/statsmodels.stats.proportion.confint_proportions_2indep.html)、[区间实现](https://www.statsmodels.org/stable/_modules/statsmodels/stats/proportion.html)、[CMH实现](https://www.statsmodels.org/stable/_modules/statsmodels/stats/contingency_tables.html)。',
        '', '## 对业务意味着什么','',
        '优先调查高加班岗位的排班、工作负荷、岗位预期和管理支持，而不是直接把减少加班当成已验证方案。后续需要有日期的纵向记录和预先设计的干预评估，才能估计措施效果。',
        '下一阶段可进入分类模型扩展，但统计关联不等于预测能力；暂未划分训练测试集，也未建模。']
    (ROOT/'reports/statistical_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    assert sha(inp)==before and sha(source)==audit['source_sha256']
    (out/'verification.json').write_text(json.dumps(dict(source_unchanged=True,processed_unchanged=True,
        formulas_checked=True,strata_totals_verified=True,source_sha256=audit['source_sha256'],processed_sha256=before),indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
