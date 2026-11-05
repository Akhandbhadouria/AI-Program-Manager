import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np
import os

os.makedirs('assets', exist_ok=True)

# 1. Executive Status & Reason Codes
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6), gridspec_kw={'width_ratios': [1, 1.3]})
fig.patch.set_facecolor('#0E1117')

# Donut Chart
statuses = ['Auto-Approved\n(3 / 23.1%)', 'Flagged Exceptions\n(6 / 46.2%)', 'Pending Review\n(4 / 30.8%)']
counts = [3, 6, 4]
colors = ['#00C49F', '#FF4B4B', '#FFBB28']
explode = (0.05, 0.05, 0.05)

wedges, texts, autotexts = ax1.pie(
    counts, labels=statuses, autopct='%1.1f%%', startangle=140,
    colors=colors, explode=explode, pctdistance=0.75,
    textprops=dict(color='white', fontsize=11, fontweight='bold')
)
for at in autotexts:
    at.set_color('black')
centre_circle = plt.Circle((0,0), 0.55, fc='#0E1117')
ax1.add_artist(centre_circle)
ax1.set_title('Reconciliation Classification (N=13 Invoices)', color='white', fontsize=13, pad=15, fontweight='bold')

# Horizontal Bar Chart for Reason Codes
reasons = [
    'Missing Faculty Form (Rhea/Arvind)',
    'Duplicate Form Submission (3308/3309)',
    'Batch Capacity Full (Batch 9205)',
    'Payment Failed at Gateway (84911)',
    'Ghost Invoice / Form Typo (84931)',
    'Promotional Discount Audit (84907)',
    'Student/Parent Info Mismatch (84904)',
    'Partial Installment 1 (84909)'
]
reason_counts = [2, 1, 1, 1, 1, 1, 1, 1]
y_pos = np.arange(len(reasons))
bar_colors = ['#FF4B4B' if i < 5 else '#FFBB28' for i in range(len(reasons))]

bars = ax2.barh(y_pos, reason_counts, align='center', color=bar_colors, height=0.6)
ax2.set_yticks(y_pos)
ax2.set_yticklabels(reasons, color='white', fontsize=10)
ax2.invert_yaxis()
ax2.set_xlabel('Affected Invoices', color='white', fontsize=11)
ax2.set_title('Root Cause Reason Codes (Exceptions & Reviews)', color='white', fontsize=13, pad=15, fontweight='bold')
ax2.set_facecolor('#1E2129')
ax2.tick_params(colors='white')
ax2.spines['top'].set_visible(False)
ax2.spines['right'].set_visible(False)
ax2.spines['left'].set_color('#444')
ax2.spines['bottom'].set_color('#444')

for bar in bars:
    width = bar.get_width()
    ax2.text(width + 0.05, bar.get_y() + bar.get_height()/2, f'{int(width)}',
             va='center', ha='left', color='white', fontweight='bold', fontsize=10)

plt.tight_layout()
plt.savefig('assets/status_and_reasons.png', dpi=200, bbox_inches='tight', facecolor='#0E1117')
plt.close()

# 2. Executive KPI Cards
fig, ax = plt.subplots(figsize=(14, 4.5))
fig.patch.set_facecolor('#0E1117')
ax.axis('off')

kpis = [
    ('Total Invoices', '13', 'Baseline Cohort', '#4A90E2'),
    ('Auto-Approved', '3 (23.1%)', 'Zero-Touch (84901-03)', '#00C49F'),
    ('Flagged Exceptions', '6 (46.2%)', 'Actionable Drafts', '#FF4B4B'),
    ('Pending Review', '4 (30.8%)', 'Human Assisted', '#FFBB28'),
    ('Stranded Baseline', '90.9%', '10 of 11 Paid Stuck', '#FF6B6B'),
    ('Automated TAT', '< 60 sec', 'vs 104.7m Manual', '#2ECC71'),
    ('Test Suite', '46 / 46', '100% Passing Tests', '#9B59B6'),
]

n = len(kpis)
card_width = 0.94 / n
for i, (title, val, sub, col) in enumerate(kpis):
    x = 0.03 + i * card_width
    rect = FancyBboxPatch((x, 0.15), card_width * 0.9, 0.7, transform=ax.transAxes,
                          boxstyle='round,pad=0.02', facecolor='#1E2129', edgecolor=col, linewidth=2, zorder=2)
    ax.add_patch(rect)
    ax.text(x + card_width * 0.45, 0.65, val, transform=ax.transAxes,
            ha='center', va='center', color=col, fontsize=15, fontweight='bold')
    ax.text(x + card_width * 0.45, 0.40, title, transform=ax.transAxes,
            ha='center', va='center', color='white', fontsize=10, fontweight='bold')
    ax.text(x + card_width * 0.45, 0.25, sub, transform=ax.transAxes,
            ha='center', va='center', color='#888', fontsize=8)

plt.title('BAMBINOS.LIVE – RECONCILIATION ENGINE PROTOTYPE TELEMETRY',
          color='white', fontsize=13, pad=18, fontweight='bold')
plt.tight_layout()
plt.savefig('assets/kpi_metrics_dashboard.png', dpi=200, bbox_inches='tight', facecolor='#0E1117')
plt.close()

# 3. Baseline vs Automated Comparison
fig, ax = plt.subplots(figsize=(10, 4.5))
fig.patch.set_facecolor('#0E1117')
ax.set_facecolor('#1E2129')

categories = ['End-to-End Turnaround Time (min)', 'Operational Hours / 500 Renewals', 'Stranded Paid Invoices Rate (%)']
baseline_vals = [104.72, 125.0, 90.9]
automated_vals = [1.0, 15.0, 0.0]

y = np.arange(len(categories))
h = 0.35

b1 = ax.barh(y + h/2, baseline_vals, h, label='Baseline Manual Process', color='#FF4B4B')
b2 = ax.barh(y - h/2, automated_vals, h, label='Automated Zero-Touch Engine', color='#00C49F')

ax.set_yticks(y)
ax.set_yticklabels(categories, color='white', fontsize=11, fontweight='bold')
ax.invert_yaxis()
ax.set_xlabel('Measurement Value (Minutes / Hours / %)', color='white', fontsize=10)
ax.set_title('Operational Efficiency Benchmark: Baseline vs Proposed Prototype', color='white', fontsize=13, pad=15, fontweight='bold')
ax.legend(facecolor='#1E2129', edgecolor='#444', labelcolor='white')
ax.tick_params(colors='white')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('#444')
ax.spines['bottom'].set_color('#444')

for bar in b1:
    w = bar.get_width()
    ax.text(w + 1.5, bar.get_y() + bar.get_height()/2, f'{w:.1f}', va='center', ha='left', color='#FF4B4B', fontweight='bold', fontsize=9)
for bar in b2:
    w = bar.get_width()
    ax.text(w + 1.5, bar.get_y() + bar.get_height()/2, f'{w:.1f}', va='center', ha='left', color='#00C49F', fontweight='bold', fontsize=9)

plt.tight_layout()
plt.savefig('assets/baseline_vs_automated.png', dpi=200, bbox_inches='tight', facecolor='#0E1117')
plt.close()

print('All 3 high-resolution visualization charts generated successfully in assets/!')

