"""阶段3–4：描述性探索与图表；不做显著性检验或模型训练。"""
from pathlib import Path
import sys
import hashlib
import json
ROOT = Path(__file__).resolve().parents[1]

import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    inp = ROOT/'data/processed/employees_clean.csv'
    before = sha(inp)
    audit = json.loads((ROOT/'reports/audit_summary.json').read_text(encoding='utf-8'))
    source = ROOT / audit['source']
    assert sha(source) == audit['source_sha256']
    d = pd.read_csv(inp)
    assert d.Attrition_Flag.equals(d.Attrition.map({'Yes':1,'No':0}))
    tables = ROOT/'reports/tables'
    figs = ROOT/'reports/figures'
    tables.mkdir(exist_ok=True)
    figs.mkdir(exist_ok=True)
    plt.rcParams.update({'font.sans-serif':['Microsoft YaHei','SimHei','DejaVu Sans'], 'axes.unicode_minus':False,'font.size':11})
    baseline = d.Attrition_Flag.mean()
    # 左闭右开：[0,2)、[2,5)、[5,10)、[10,+∞)。0含不足一年的记录。
    d['TenureBand'] = pd.cut(d.YearsAtCompany, [0,2,5,10,float('inf')],right=False,labels=['0–1年','2–4年','5–9年','10年以上'])
    groups = {}
    def group(keys, name):
        t=d.groupby(keys,observed=True,dropna=False).Attrition_Flag.agg(employees='size',leavers='sum').reset_index()
        t['attrition_rate']=t.leavers/t.employees
        t['small_sample']=t.employees<30
        assert t.employees.sum()==len(d) and t.leavers.sum()==d.Attrition_Flag.sum()
        t.to_csv(tables/(name+'.csv'),index=False,encoding='utf-8-sig')
        groups[name]=t
        return t
    for c in ['Department','JobRole','OverTime','TenureBand','JobSatisfaction','EnvironmentSatisfaction','WorkLifeBalance','JobLevel','TrainingTimesLastYear','YearsSinceLastPromotion']:
        group([c],c)
    for c in ['JobRole','JobLevel']:
        group([c,'OverTime'],c+'_OverTime')
    income=d.groupby(['JobRole','JobLevel','Attrition'],observed=True).MonthlyIncome.agg(employees='size',median_income='median',mean_income='mean').reset_index()
    income['small_sample']=income.employees<30
    assert income.employees.sum()==len(d)
    income.to_csv(tables/'income_by_role_level_status.csv',index=False,encoding='utf-8-sig')
    # 同岗位且同职级内划分相对收入；并列中位数归入“中位数及以上”。
    median=d.groupby(['JobRole','JobLevel']).MonthlyIncome.transform('median')
    d['RelativeIncome']=pd.Series('中位数及以上',index=d.index).where(d.MonthlyIncome>=median,'低于组内中位数')
    relative=group(['JobRole','JobLevel','RelativeIncome'],'relative_income_strata')
    overall_income=d.groupby('Attrition').MonthlyIncome.agg(employees='size',median_income='median',mean_income='mean')
    overall_income.to_csv(tables/'income_by_status.csv',encoding='utf-8-sig')

    def save(fig,name):
        fig.savefig(figs/(name+'.png'),dpi=160,bbox_inches='tight')
        plt.close(fig)
    def rateplot(ax,t,key,title):
        t=t.reset_index(drop=True)
        ax.barh(range(len(t)),t.attrition_rate,color='#287D8E')
        ax.set_yticks(range(len(t)),[str(x) for x in t[key]])
        for i,r in t.iterrows():
            ax.text(r.attrition_rate+.008,i,f'{r.attrition_rate:.1%} ({r.leavers}/{r.employees})'+(' *' if r.small_sample else ''),va='center',fontsize=9)
        ax.axvline(baseline,color='#BF6846',linestyle='--',label=f'总体 {baseline:.2%}')
        ax.set_xlim(0,max(.45,float(t.attrition_rate.max())+.22))
        ax.xaxis.set_major_formatter(PercentFormatter(1))
        ax.set_xlabel('样本离职比例（离职人数 / 本组人数）；* 本组人数<30')
        ax.set_title(title)
        ax.invert_yaxis()
        ax.legend(loc='lower right',fontsize=8)
        ax.spines[['top','right']].set_visible(False)
    fig,ax=plt.subplots(figsize=(9,5))
    counts=d.Attrition.value_counts().reindex(['No','Yes'])
    ax.bar(['未离职','离职'],counts,color=['#287D8E','#BF6846'])
    for i,v in enumerate(counts): ax.text(i,v+20,f'{v}人 ({v/len(d):.2%})',ha='center')
    ax.set_ylim(0,1450);ax.set_ylabel('人数');ax.set_title(f'样本构成：分母为全部{len(d)}名员工（非年度离职率）')
    save(fig,'01_overview')
    fig,axes=plt.subplots(2,1,figsize=(13,11),gridspec_kw={'height_ratios':[1,2]},layout='constrained')
    for ax,c in zip(axes,['Department','JobRole']):rateplot(ax,groups[c].sort_values('attrition_rate',ascending=False),c,'部门对比' if c=='Department' else '岗位对比')
    save(fig,'02_department_role')
    fig,ax=plt.subplots(figsize=(10,4));rateplot(ax,groups['OverTime'],'OverTime','加班与离职：Yes=加班，No=不加班（关联不代表因果）');save(fig,'03_overtime')
    fig,ax=plt.subplots(figsize=(9,5))
    vals=[d.loc[d.Attrition==v,'MonthlyIncome'] for v in ['No','Yes']]
    ax.boxplot(vals,tick_labels=[f'未离职 n={len(vals[0])}',f'离职 n={len(vals[1])}'],showfliers=True)
    ax.set_ylabel('MonthlyIncome（币种未知）');ax.set_title('月收入分布：线为中位数，箱体为中间50%\n总体比较未控制岗位和职级；极端值保留')
    save(fig,'04_income')
    fig,ax=plt.subplots(figsize=(10,5));rateplot(ax,groups['TenureBand'],'TenureBand','在公司年数与样本离职比例');save(fig,'05_tenure')
    fig,axes=plt.subplots(3,1,figsize=(11,12),layout='constrained')
    for ax,c,title in zip(axes,['JobSatisfaction','EnvironmentSatisfaction','WorkLifeBalance'],['工作满意度','环境满意度','工作生活平衡']):rateplot(ax,groups[c],c,title+'等级（数字为原始编码）')
    save(fig,'06_satisfaction')

    def table(t,keys):
        lines=['|分组|人数|离职人数|离职比例|提示|','|---|---:|---:|---:|---|']
        for _,r in t.iterrows():lines.append('|'+ ' / '.join(str(r[k]) for k in keys)+f'|{r.employees}|{r.leavers}|{r.attrition_rate:.2%}|'+('样本<30' if r.small_sample else '')+'|')
        return '\n'.join(lines)
    ot=groups['OverTime'].set_index('OverTime')
    roles=groups['JobRole'].sort_values('attrition_rate',ascending=False)
    top=roles.iloc[0]
    tenure=groups['TenureBand'].set_index('TenureBand')
    sat=groups['JobSatisfaction'].set_index('JobSatisfaction')
    findings=[
        f'加班组离职{int(ot.loc["Yes","leavers"])} / {int(ot.loc["Yes","employees"])}人（{ot.loc["Yes","attrition_rate"]:.2%}），不加班组{int(ot.loc["No","leavers"])} / {int(ot.loc["No","employees"])}人（{ot.loc["No","attrition_rate"]:.2%}），相差{100*(ot.loc["Yes","attrition_rate"]-ot.loc["No","attrition_rate"]):.2f}个百分点。需要进一步排查岗位构成，不能解释为加班的因果效果。',
        f'岗位中{top.JobRole}的观察比例最高：{int(top.leavers)}/{int(top.employees)}（{top.attrition_rate:.2%}）。排序只是当前样本描述，不等于稳定风险排名。',
        f'在公司0–1年组离职{int(tenure.loc["0–1年","leavers"])}/{int(tenure.loc["0–1年","employees"])}（{tenure.loc["0–1年","attrition_rate"]:.2%}）。值得调查新人融入过程；快照比较也受到留存选择影响，不能估计员工随时间变化的离职概率。',
        f'工作满意度编码1组为{int(sat.loc[1,"leavers"])}/{int(sat.loc[1,"employees"])}（{sat.loc[1,"attrition_rate"]:.2%}），编码4组为{int(sat.loc[4,"leavers"])}/{int(sat.loc[4,"employees"])}（{sat.loc[4,"attrition_rate"]:.2%}）。评分测量时间未知，不能断定满意度变化先于离职。',
        f'离职组月收入中位数{overall_income.loc["Yes","median_income"]:,.0f}（n={int(overall_income.loc["Yes","employees"])}），未离职组{overall_income.loc["No","median_income"]:,.0f}（n={int(overall_income.loc["No","employees"])}）。这是总体构成差异，不能直接认定加薪可以留人。已另存同岗位同职级的比较表，小组人数不足时不下结论。'
    ]
    lines=['# 探索性分析报告（阶段3–4）','','公开模拟HR数据；无日期；所有比例是样本离职比例，不是年度离职率。没有进行统计显著性检验、置信区间估计或模型训练。','',
        '## 怎么理解这些数字','','每组离职比例=该组离职人数÷该组人数。人数和比例必须一起看；小于30人的组仅提示不稳定，不是统计学上的绝对阈值。图中虚线为总体16.12%。','',
        '## 五条主要发现','']+[f'{i+1}. {x}' for i,x in enumerate(findings)]
    for name,title,image in [('Department','部门','02_department_role'),('JobRole','岗位',None),('OverTime','加班','03_overtime'),('TenureBand','在公司年数','05_tenure'),('JobSatisfaction','工作满意度','06_satisfaction'),('EnvironmentSatisfaction','环境满意度',None),('WorkLifeBalance','工作生活平衡',None)]:
        lines+=['',f'## {title}','',table(groups[name],[name])]
        if image:lines+=['',f'![{title}](figures/{image}.png)']
    lines+=['','## 收入分析为什么要分层','','![收入分布](figures/04_income.png)',
        '不同岗位和职级本来就可能收入不同。`tables/income_by_role_level_status.csv`按岗位、职级和离职标签给出人数、中位数、均值；`relative_income_strata.csv`在每个岗位×职级内按收入是否低于本组中位数分组。并列中位数归入“中位数及以上”，不存在的组合不补零。没有把这些细组简单平均，也没有把分层描述说成已控制全部混杂因素。',
        '', '## 其他探索表','','培训次数、晋升间隔、职级表已保存在tables目录。岗位×加班、职级×加班表供下一阶段分层统计使用；本轮不凭大量探索比较挑选“显著”结论。',
        '', '## 可以进一步验证的业务方向','','- 调查加班较多岗位的工作负荷与排班；先验证岗位差异，再考虑措施。',
        '- 访谈入职0–1年的员工，检查培训、导师支持和岗位预期是否匹配。',
        '- 联合岗位与职级审查薪酬和成长机会；不根据个体预测或单一人口属性作人事决定。',
        '以上是调查方向，不是已证明有效的留任措施，也没有测算节省金额。',
        '', '## 下一步','','阶段5：以加班为主问题，计算比例差及95%置信区间、卡方检验，并检查岗位/职级分层。待确认后执行；暂不建模。']
    (ROOT/'reports/eda_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    assert sha(inp)==before and sha(source)==audit['source_sha256']
    verification=dict(rows=len(d),leavers=int(d.Attrition_Flag.sum()),group_tables_verified=len(groups),figures=6,processed_unchanged=True,source_unchanged=True,models_trained=False,matplotlib_version=matplotlib.__version__)
    (ROOT/'reports/eda_verification.json').write_text(json.dumps(verification,indent=2),encoding='utf-8')
    print('\n'.join(findings))
    print(json.dumps(verification))

if __name__=='__main__':main()
