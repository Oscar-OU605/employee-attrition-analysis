"""阶段6–7：分层划分、训练集调参、最后一次测试评估和双语报告。"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]

import hashlib
import json
import warnings
import numpy as np
import pandas as pd
import sklearn
import scipy
import joblib
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.dummy import DummyClassifier
from sklearn.model_selection import train_test_split, StratifiedKFold, GridSearchCV
from sklearn.metrics import precision_score, recall_score, f1_score, average_precision_score, roc_auc_score, accuracy_score, confusion_matrix
from sklearn.exceptions import ConvergenceWarning
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.metrics import PrecisionRecallDisplay, RocCurveDisplay

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write_json(p,d):p.write_text(json.dumps(d,indent=2,ensure_ascii=False,default=str),encoding='utf-8')

def main():
    warnings.filterwarnings('error',category=ConvergenceWarning)
    inp=ROOT/'data/processed/employees_clean.csv'
    source_info=json.loads((ROOT/'reports/audit_summary.json').read_text(encoding='utf-8'))
    source=ROOT / source_info['source']
    before=sha(inp)
    assert sha(source)==source_info['source_sha256']
    d=pd.read_csv(inp)
    contract=json.loads((ROOT/'data/processed/feature_contract.json').read_text(encoding='utf-8'))
    features=contract['features']
    assert not set(features)&set(contract['excluded']+[contract['target']])
    assert d.Attrition_Flag.equals(d.Attrition.map({'Yes':1,'No':0}))
    assert not d.EmployeeNumber.duplicated().any()
    X,y=d[features],d[contract['target']]
    assert not X.isna().any().any()
    # 先分割，再拟合编码器/标准化器。测试集不参与模型、权重或超参数选择。
    train,test=train_test_split(np.arange(len(d)),test_size=.2,stratify=y,random_state=42)
    assert not set(train)&set(test) and len(set(train)|set(test))==len(d)
    xt,yt=X.iloc[train],y.iloc[train]
    xv,yv=X.iloc[test],y.iloc[test]
    categorical=['BusinessTravel','Department','EducationField','JobRole',
        'Education','EnvironmentSatisfaction','JobInvolvement','JobLevel','JobSatisfaction',
        'PerformanceRating','RelationshipSatisfaction','StockOptionLevel','WorkLifeBalance']
    # 评分也独热编码，避免逻辑回归强行假定相邻评分间距相同。
    numeric=[c for c in features if c not in categorical]
    output=ROOT/'reports/modeling';output.mkdir(exist_ok=True)
    models_dir=ROOT/'models';models_dir.mkdir(exist_ok=True)
    split=pd.DataFrame({'EmployeeNumber':d.EmployeeNumber,'split':'train'})
    split.loc[test,'split']='test'
    split.to_csv(output/'split_assignment.csv',index=False,encoding='utf-8-sig')
    cv=StratifiedKFold(n_splits=5,shuffle=True,random_state=42)
    folds=list(cv.split(xt,yt))
    for a,b in folds:assert not set(a)&set(b)
    cv_assignment=[]
    for i,(_,valid) in enumerate(folds):
        cv_assignment.extend({'EmployeeNumber':int(d.iloc[train[j]].EmployeeNumber),'validation_fold':i+1} for j in valid)
    pd.DataFrame(cv_assignment).to_csv(output/'cv_assignment.csv',index=False)
    def preprocess(scale):
        return ColumnTransformer([('numeric',StandardScaler() if scale else 'passthrough',numeric),
            ('category',OneHotEncoder(handle_unknown='ignore',sparse_output=False),categorical)])
    specs={
        'logistic_regression':(Pipeline([('prepare',preprocess(True)),('model',LogisticRegression(max_iter=3000,solver='lbfgs',random_state=42))]),
            {'model__C':[.1,1.,10.],'model__class_weight':[None,'balanced']}),
        'random_forest':(Pipeline([('prepare',preprocess(False)),('model',RandomForestClassifier(n_estimators=300,random_state=42,n_jobs=1))]),
            {'model__max_depth':[5,None],'model__min_samples_leaf':[1,5],'model__class_weight':[None,'balanced']})}
    fitted={};selection=[]
    for name,(pipe,grid) in specs.items():
        print('Training',name,flush=True)
        search=GridSearchCV(pipe,grid,scoring='average_precision',cv=folds,refit=True,n_jobs=1,error_score='raise',return_train_score=True)
        search.fit(xt,yt)
        pd.DataFrame(search.cv_results_).to_csv(output/(name+'_cv.csv'),index=False,encoding='utf-8-sig')
        fitted[name]=search.best_estimator_
        selection.append(dict(model=name,cv_ap=search.best_score_,cv_ap_std=float(search.cv_results_['std_test_score'][search.best_index_]),best_params=search.best_params_))
        joblib.dump(search.best_estimator_,models_dir/(name+'.joblib'))
    # 在查看任何测试成绩之前冻结选择：最高训练集CV AP；并列优先逻辑回归。
    chosen=max(selection,key=lambda r:r['cv_ap'])['model']
    write_json(output/'selection_before_test.json',dict(selected=chosen,criterion='training five-fold mean average precision',models=selection,threshold=.5))
    dummy=DummyClassifier(strategy='most_frequent').fit(xt,yt)
    fitted={'majority_baseline':dummy,**fitted}
    rows=[];predictions=pd.DataFrame({'EmployeeNumber':d.iloc[test].EmployeeNumber.to_numpy(),'actual':yv.to_numpy()})
    scores={}
    for name,model in fitted.items():
        prob=model.predict_proba(xv)[:,1]
        pred=(prob>=.5).astype(int)
        tn,fp,fn,tp=confusion_matrix(yv,pred,labels=[0,1]).ravel()
        assert tn+fp+fn+tp==len(test) and fn+tp==int(yv.sum())
        rows.append(dict(model=name,accuracy=accuracy_score(yv,pred),precision=precision_score(yv,pred,zero_division=0),
            recall=recall_score(yv,pred),f1=f1_score(yv,pred),average_precision=average_precision_score(yv,prob),
            roc_auc=roc_auc_score(yv,prob),tn=int(tn),fp=int(fp),fn=int(fn),tp=int(tp)))
        predictions[name+'_score']=prob;predictions[name+'_prediction']=pred;scores[name]=prob
    metrics=pd.DataFrame(rows);metrics.to_csv(output/'test_metrics.csv',index=False)
    predictions.to_csv(output/'test_predictions.csv',index=False)
    # 保存后重新加载，确认序列化不改变预测，不重训、不重新选模型。
    for name in specs:
        restored=joblib.load(models_dir/(name+'.joblib'))
        assert np.allclose(restored.predict_proba(xv)[:,1],scores[name])
    lr=fitted['logistic_regression']
    coef=pd.DataFrame({'feature':lr.named_steps['prepare'].get_feature_names_out(),'coefficient':lr.named_steps['model'].coef_[0]})
    coef['absolute_coefficient']=coef.coefficient.abs()
    coef.sort_values('absolute_coefficient',ascending=False).to_csv(output/'logistic_coefficients.csv',index=False)
    # 确认标准化器仅学习训练集均值。
    assert np.allclose(lr.named_steps['prepare'].named_transformers_['numeric'].mean_,xt[numeric].mean().to_numpy())
    fig,axes=plt.subplots(1,2,figsize=(12,5),layout='constrained')
    for name,prob in scores.items():
        PrecisionRecallDisplay.from_predictions(yv,prob,name=name,ax=axes[0])
        RocCurveDisplay.from_predictions(yv,prob,name=name,ax=axes[1])
    axes[0].axhline(yv.mean(),color='gray',linestyle='--',label='Test prevalence')
    axes[0].set_title('Held-out precision-recall curves');axes[1].set_title('Held-out ROC curves')
    axes[0].legend(fontsize=8);axes[1].legend(fontsize=8)
    fig.savefig(output/'evaluation_curves.png',dpi=160);plt.close(fig)
    manifest=dict(train_n=len(train),test_n=len(test),train_leavers=int(yt.sum()),test_leavers=int(yv.sum()),
        seed=42,threshold=.5,selected_model=chosen,features=features,numeric=numeric,categorical=categorical,
        train_test_disjoint=True,source_unchanged=sha(source)==source_info['source_sha256'],processed_unchanged=sha(inp)==before,
        pipeline_reload_predictions_match=True,scaler_matches_training_only=True,sklearn=sklearn.__version__,scipy=scipy.__version__,
        numpy=np.__version__,pandas=pd.__version__,python=sys.version,joblib=joblib.__version__,source_sha256=source_info['source_sha256'],processed_sha256=before)
    assert manifest['source_unchanged'] and manifest['processed_unchanged']
    write_json(output/'verification.json',manifest)
    def metric_table():
        lines=['|Model|Accuracy|Precision|Recall|F1|AP|ROC-AUC|TN|FP|FN|TP|','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
        for r in rows:lines.append('|'+r['model']+'|'+ '|'.join(f'{r[k]:.3f}' for k in ['accuracy','precision','recall','f1','average_precision','roc_auc'])+'|'+ '|'.join(str(r[k]) for k in ['tn','fp','fn','tp'])+'|')
        return '\n'.join(lines)
    best=next(r for r in rows if r['model']==chosen)
    cvtext='\n'.join(f"- {s['model']}: CV AP={s['cv_ap']:.4f}, fold SD={s['cv_ap_std']:.4f}; {s['best_params']}" for s in selection)
    for lang in ['zh','en']:
        if lang=='zh':
            body=[ '# 员工离职分类模型报告（阶段6–7）','',
                f"训练集{len(train)}人（离职{int(yt.sum())}），测试集{len(test)}人（离职{int(yv.sum())}）。按标签分层80/20划分，随机种子42。先划分再拟合预处理，训练集5折交叉验证，依据平均AP选择参数与模型。阈值固定0.5，没有根据测试集调整。",'',
                '## 为什么用这些模型','',
                '基准模型全部猜不离职，用来揭示高准确率可能毫无识别能力。逻辑回归简单、可解释；随机森林捕捉非线性和交互关系。比较默认类别权重和balanced，后者增加少数类在训练中的权重，但不保证召回率一定更高。',
                '排除编号、三个常量、年龄、性别、婚姻状况及原始目标。评分和类别均独热编码，避免把评分间距强行视为相同；逻辑回归的其余数值字段标准化。随机森林不做标准化。全部处理在Pipeline内，每折只学习该折训练数据。未知类别忽略为全零编码。没有SMOTE、异常值删除或测试集调参。','',
                '## 训练集内选择','',cvtext,'',f'在查看测试成绩前选定：**{chosen}**。CV标准差表示五折波动，不是95%置信区间；参数搜索中的最优CV成绩可能偏乐观。','',
                '## 留出的测试集成绩','',metric_table(),'',
                f"选定模型找出了{best['tp']}名离职员工，漏掉{best['fn']}名，并把{best['fp']}名未离职员工误报为离职。",
                'Precision：预测会离职的人中有多少真的离职；Recall：实际离职的人中找出了多少；F1平衡两者。AP衡量不同阈值下对少数类的排序能力，不等于准确率，也不是梯形积分的PR面积。ROC-AUC比较正负样本排序。TN=正确识别未离职，FP=误报，FN=漏报，TP=正确识别离职。基准模型没有预测正例，Precision按约定记0。',
                '预测分数未做概率校准，不能直接解释为真实员工未来离职概率；0.5仅为默认阈值，不是已优化的业务决策点。','',
                '![测试集评估曲线](modeling/evaluation_curves.png)','',
                '## 解释与限制','',
                '逻辑回归系数另存CSV。数值系数对应标准化单位；独热编码未删基准类别且使用正则化，不能把某系数直接当作相对明确参考组的因果效应。相关特征可能分摊或改变系数。',
                '数据是模拟快照；没有测量和离职日期，不能保证特征发生于离职前。先前已经检查全样本分布，因此这是教学项目内部评估，不是完全未接触数据的外部验证。单次测试集仅有少量离职记录，成绩会随划分波动。删除人口属性不自动保证公平。',
                '只凭训练集CV选择模型；同时列出两种模型的最终测试成绩用于透明比较，不能再据此反复调参。没有宣称降低离职率、节省成本或可部署。模型文件只应加载自己生成且可信的文件。','',
                '## 下一步业务验证','',
                '优先把结果用于群体层面的工作负荷、入职支持和职业发展调查。若有真实新数据，再检查时间顺序、外部表现、概率校准、公平性及业务成本，决定是否需要改变阈值。']
        else:
            body=['# Employee attrition classification report (Stages 6–7)','',
                f"Stratified 80/20 split, seed 42: training n={len(train)} ({int(yt.sum())} leavers), test n={len(test)} ({int(yv.sum())} leavers). All preprocessing is fitted after splitting. Five-fold training-only cross-validation selects hyperparameters and the model using mean average precision (AP). The threshold remains 0.5; test results never determine parameters or threshold.",
                '', '## Models and preprocessing','',
                'The majority baseline predicts no attrition for everyone. Logistic regression provides a simpler model; random forest captures nonlinear patterns and interactions. Default and balanced class weights are compared; balanced weights do not guarantee higher recall.',
                'Employee ID, three constant fields, age, gender, marital status and the original target are excluded. Categorical and rating fields are one-hot encoded to avoid assuming equal spacing of ratings. Remaining numeric inputs are standardized for logistic regression only. Each fold fits its own preprocessing through a Pipeline; unknown categories map to all-zero indicators. No SMOTE, outlier removal or test-set tuning.',
                '', '## Training-only selection','',cvtext,'',f'Frozen before test evaluation: **{chosen}**. Fold SD describes five-fold variability, not a 95% confidence interval. The best search CV score can be optimistic.',
                '', '## Held-out test evaluation','',metric_table(),'',
                f"The selected model identified {best['tp']} leavers, missed {best['fn']}, and falsely flagged {best['fp']} non-leavers.",
                'Precision measures correctness among positive predictions; recall measures coverage of actual leavers; F1 balances them. AP summarizes positive-class ranking across thresholds, not accuracy or trapezoidal PR area. ROC-AUC measures positive-versus-negative ranking. TN/FP/FN/TP denote true negatives, false positives, false negatives and true positives. Baseline precision is set to zero because there are no positive predictions.',
                'Scores are not calibrated probabilities of future attrition. The default 0.5 threshold is not an optimized business decision rule.',
                '', '![Evaluation curves](modeling/evaluation_curves.png)','',
                '## Interpretation and limitations','',
                'Logistic coefficients are saved separately. Numeric coefficients use standardized units. Full one-hot encoding with regularization does not provide causal contrasts against one omitted reference category; correlated inputs also affect coefficients.',
                'These are fictional snapshots with unknown measurement and attrition timing, so temporal leakage cannot be ruled out. Full-sample distributions were previously explored: this is an internal educational evaluation, not untouched external validation. A single small test set is unstable. Excluding demographic inputs does not establish fairness.',
                'Both final test results are shown transparently, but model choice was frozen using training CV. Do not tune repeatedly against this test set. No retention gains, cost savings or deployment readiness are claimed. Load only trusted model files you generated.',
                '', '## Business follow-up','',
                'Use the analysis to guide aggregate investigations of workload, onboarding and career development. Real deployment would require new time-stamped data, external evaluation, calibration, fairness assessment and explicit business costs before changing thresholds.']
        body+=['','References: [scikit-learn leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html).']
        (ROOT/'reports'/('model_report_'+lang+'.md')).write_text('\n'.join(body)+'\n',encoding='utf-8')
    print(metrics.to_string(index=False),flush=True)
    print('Selected by training CV:',chosen,flush=True)

if __name__=='__main__':main()
