"""Render portfolio figures from verified, frozen results; never fit a model."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
result = json.loads((ROOT / 'reports/test_metrics.json').read_text())
output = ROOT / 'reports/figures'
output.mkdir(exist_ok=True)
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11, 'axes.spines.top': False,
                     'axes.spines.right': False, 'figure.facecolor': '#f8fafc', 'axes.facecolor': '#f8fafc',
                     'savefig.facecolor': '#f8fafc'})
blue, teal, gray = '#2563eb', '#0f766e', '#94a3b8'

budgets = result['review']['budgets']
fig, axes = plt.subplots(1, 2, figsize=(12, 4.9))
x = np.arange(2)
prior = [v['uncertainty_priority']['n_errors_found'] for v in budgets]
random = [v['uniform_random']['expected']['n_errors_found'] for v in budgets]
axes[0].bar(x - .17, random, .32, label='Uniform random (expectation)', color=gray)
axes[0].bar(x + .17, prior, .32, label='Low-confidence Exact first', color=blue)
for at, values in [(-.17, random),(.17,prior)]:
    for i,value in enumerate(values):
        axes[0].text(i+at,value+130,f'{value:,.0f}',ha='center',fontsize=10)
axes[0].set_xticks(x, [f"{v['budget_fraction']:.0%} of pool\n{v['n_reviewed']:,} inspections" for v in budgets])
axes[0].set_ylim(0, 8100)
axes[0].set_ylabel('Model errors found using published labels')
axes[0].set_title('Same pool, same number of inspections',loc='left',fontweight='bold')
axes[0].legend(frameon=False,fontsize=9,loc='upper left')
ci = result['uncertainty']
ys = [ci['random_expected_yield'], ci['audit_yield']]
axes[1].barh([0,1],[v['point']*100 for v in ys],color=[gray,blue],height=.5)
axes[1].errorbar([v['point']*100 for v in ys],[0,1],
    xerr=np.array([[v['point']-v['low'] for v in ys],[v['high']-v['point'] for v in ys]])*100,
    fmt='none',ecolor='#0f172a',capsize=5)
axes[1].set_yticks([0,1],['Random','Priority'])
axes[1].set_xlim(0,42)
for i,v in enumerate(ys):
    axes[1].text(v['high']*100+1,i,f"{v['point']:.1%}",va='center',fontweight='bold')
axes[1].set_xlabel('Errors per 100 inspections (%)')
axes[1].set_title('10% budget: audit yield',loc='left',fontweight='bold')
fig.suptitle('Search-quality review: use a limited audit budget more effectively',x=.06,ha='left',fontsize=15,fontweight='bold')
fig.text(.06,.02,'Official US test pairs | Fixed model | 95% query-cluster bootstrap intervals | Offline simulation; no business lift measured',fontsize=9,color='#475569')
fig.tight_layout(rect=[0,.06,1,.92])
fig.savefig(output/'review_priority.png',dpi=160,bbox_inches='tight')
plt.close(fig)

fig,axes=plt.subplots(1,2,figsize=(12,4.9))
c=result['classification']; base=result['majority_baseline']
labels=c['labels']
axes[0].bar(np.arange(4),[c['per_class'][s]['f1'] for s in labels],color=[teal,blue,gray,'#6366f1'])
axes[0].set_xticks(np.arange(4),['Exact','Substitute','Complement','Irrelevant'])
axes[0].set_ylim(0,.85)
axes[0].set_ylabel('Per-class F1')
for i,s in enumerate(labels):
    axes[0].text(i,c['per_class'][s]['f1']+.02,f"{c['per_class'][s]['f1']:.3f}",ha='center')
axes[0].set_title('Complement recognition remains weak',loc='left',fontweight='bold')
axes[1].bar(x-.17,[base['accuracy'],base['macro_f1']],.32,color=gray,label='Majority baseline')
axes[1].bar(x+.17,[c['accuracy'],c['macro_f1']],.32,color=blue,label='Weighted logistic model')
axes[1].set_xticks(x,['Accuracy','Macro-F1'])
axes[1].set_ylim(0,.85)
for at,values in [(-.17,[base['accuracy'],base['macro_f1']]),(.17,[c['accuracy'],c['macro_f1']])]:
    for i,v in enumerate(values):
        axes[1].text(i+at,v+.02,f'{v:.3f}',ha='center')
axes[1].legend(frameon=False,fontsize=9)
axes[1].set_title('Class balance creates a real tradeoff',loc='left',fontweight='bold')
fig.suptitle('A useful audit signal with substantial classification limits',x=.06,ha='left',fontsize=15,fontweight='bold')
fig.text(.06,.02,'425,762 official US test pairs | 22,458 queries | Model selected only on validation macro-F1 | No automated deployment recommended',fontsize=9,color='#475569')
fig.tight_layout(rect=[0,.06,1,.92])
fig.savefig(output/'classification_tradeoff.png',dpi=160,bbox_inches='tight')
plt.close(fig)
print('Built two figures from reports/test_metrics.json')
