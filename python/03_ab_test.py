
import sqlite3, numpy as np, pandas as pd
from scipy import stats
from statsmodels.stats.proportion import (proportions_ztest,
    proportion_confint, proportion_effectsize)
from statsmodels.stats.power import NormalIndPower

con = sqlite3.connect('data/prizepicks.db')

# retained_30 = made >=1 entry between day 23 and 37 after signup (a proxy).
# net_rev = entry fees - payouts over the first 30 days.
q = '''
WITH e AS (
  SELECT p.player_id, p.exp_group, p.value_tier,
    MAX(CASE WHEN julianday(en.entry_date)-julianday(p.signup_date)
             BETWEEN 23 AND 37 THEN 1 ELSE 0 END) AS retained_30
  FROM players p LEFT JOIN entries en ON en.player_id=p.player_id
  WHERE p.exp_group IN ('treatment','control')
  GROUP BY p.player_id, p.exp_group, p.value_tier),
rev AS (
  SELECT p.player_id,
    COALESCE(SUM(en.entry_fee),0)-COALESCE(SUM(en.payout),0) AS net_rev
  FROM players p LEFT JOIN entries en ON en.player_id=p.player_id
    AND julianday(en.entry_date)-julianday(p.signup_date) <= 30
  WHERE p.exp_group IN ('treatment','control')
  GROUP BY p.player_id)
SELECT e.*, rev.net_rev, COALESCE(b.bonus_cost,0) AS bonus_cost
FROM e JOIN rev USING(player_id) LEFT JOIN bonus b USING(player_id);
'''
df = pd.read_sql(q, con)
con.close()

t = df[df.exp_group == 'treatment']
c = df[df.exp_group == 'control']
print(f'N treatment={len(t)}, N control={len(c)}')

# 1) RETENTION: two-proportion z-test ----------------------------------
succ = np.array([t.retained_30.sum(), c.retained_30.sum()])
nobs = np.array([len(t), len(c)])
z, p_ret = proportions_ztest(succ, nobs, alternative='larger')
rt, rc = succ / nobs
print(f'Retention treat={rt:.3f} ctrl={rc:.3f} lift={rt-rc:+.3f} p={p_ret:.4f}')
print('  95% CI treat', proportion_confint(succ[0], nobs[0], method='wilson'))
print('  95% CI ctrl ', proportion_confint(succ[1], nobs[1], method='wilson'))

# 2) was the sample big enough? (post-hoc power) -----------------------
es = proportion_effectsize(rt, rc)
power = NormalIndPower().power(es, nobs1=len(t), ratio=len(c) / len(t),
        alpha=0.05, alternative='larger')
print(f'effect size h={es:.3f}  power={power:.2f}')

# 3) REVENUE: Welch t-test ---------------------------------------------
tt, p_rev = stats.ttest_ind(t.net_rev, c.net_rev, equal_var=False)
print(f'Net rev/player treat=${t.net_rev.mean():.2f} '
      f'ctrl=${c.net_rev.mean():.2f} p={p_rev:.4f}')

# 4) REINVESTMENT ROI --------------------------------------------------
extra = (t.net_rev.mean() - c.net_rev.mean()) * len(t)
spend = t.bonus_cost.sum()
print(f'Bonus spend=${spend:,.0f}  incremental rev=${extra:,.0f}  '
      f'ROI={(extra-spend)/spend:+.1%}')

# 5) THE SEGMENT TWIST (your headline) + export for Tableau -----------
rows = []
print('\n--- ROI by value tier ---')
for tier in ['low', 'mid', 'high']:
    tt2 = t[t.value_tier == tier]
    cc2 = c[c.value_tier == tier]
    inc = (tt2.net_rev.mean() - cc2.net_rev.mean()) * len(tt2)
    sp = tt2.bonus_cost.sum()
    r = (inc - sp) / sp if sp else float('nan')
    lift = tt2.retained_30.mean() - cc2.retained_30.mean()
    print(f'{tier:>4}: ret lift={lift:+.3f}  ROI={r:+.1%}  spend=${sp:,.0f}')
    rows.append({'tier': tier,
                 'treat_ret': tt2.retained_30.mean(),
                 'ctrl_ret': cc2.retained_30.mean(),
                 'roi': r})
pd.DataFrame(rows).to_csv('data/ab_by_tier.csv', index=False)
print('\nSaved data/ab_by_tier.csv for Tableau.')