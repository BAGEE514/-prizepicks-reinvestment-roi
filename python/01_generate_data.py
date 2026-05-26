import numpy as np, pandas as pd, sqlite3, os
from datetime import datetime, timedelta

rng = np.random.default_rng(42)        # reproducible: same data every run
N = 20000                              # number of players
START = datetime(2025, 1, 1)

# ---------- players ----------
channels = ['Paid Social', 'Influencer', 'Organic', 'Referral', 'App Store']
ch_p     = [0.34, 0.22, 0.20, 0.14, 0.10]
states   = ['GA', 'TX', 'FL', 'NY', 'CA', 'OH', 'IL', 'PA', 'MI', 'AZ']
tier = rng.choice(['low', 'mid', 'high'], N, p=[0.55, 0.33, 0.12])
signup_offset = rng.integers(0, 120, N)        # signed up over ~4 months
players = pd.DataFrame({
    'player_id': np.arange(1, N + 1),
    'signup_date': [START + timedelta(days=int(d)) for d in signup_offset],
    'acquisition_channel': rng.choice(channels, N, p=ch_p),
    'state': rng.choice(states, N),
    'value_tier': tier,
})

# ---------- A/B experiment: enrollment window = signup days 15..59 ----------
# (a ~6-week window; widened so the revenue analysis has enough players)
in_window = (signup_offset >= 15) & (signup_offset <= 59)
group = np.where(in_window,
                 rng.choice(['treatment', 'control'], N, p=[0.5, 0.5]),
                 'not_enrolled')
players['exp_group'] = group

# ---------- hidden 'truth' the A/B test must recover ----------
# base 30-day retention by tier; the bonus (treatment) adds a lift that is
# big for mid, moderate for high, ~zero for low (the segment story).
base_ret = players['value_tier'].map({'low': 0.18, 'mid': 0.34, 'high': 0.52}).values
lift = np.where(players['exp_group'].values == 'treatment',
                players['value_tier'].map({'low': 0.004, 'mid': 0.15, 'high': 0.10}).values,
                0.0)
ret_prob = np.clip(base_ret + lift, 0, 0.95)
retained_30 = rng.random(N) < ret_prob       # ground-truth retention flag

# ---------- deposits ----------
dep_rows = []
tier_dep = {'low': (1, 15), 'mid': (3, 45), 'high': (6, 120)}   # (count_lambda, avg$)
for i, row in players.iterrows():
    lam, avg = tier_dep[row.value_tier]
    n_dep = rng.poisson(lam * (1.6 if retained_30[i] else 1.0)) + 1
    for _ in range(n_dep):
        day = rng.integers(0, 60)
        amt = round(float(rng.gamma(2.0, avg / 2.0)), 2)
        dep_rows.append((row.player_id,
                         row.signup_date + timedelta(days=int(day)), amt))
deposits = pd.DataFrame(dep_rows, columns=['player_id', 'deposit_date', 'amount'])
deposits.insert(0, 'deposit_id', np.arange(1, len(deposits) + 1))

# reinvestment BONUS COST: treatment got a 15% match (capped $12) on 1st deposit
first_dep = (deposits.sort_values('deposit_date')
                     .groupby('player_id', as_index=False).first())
g = players.set_index('player_id')['exp_group']
first_dep['bonus_cost'] = np.where(
    first_dep['player_id'].map(g) == 'treatment',
    np.minimum(first_dep['amount'] * 0.15, 12.0), 0.0)
bonus = first_dep[['player_id', 'bonus_cost']]

# ---------- entries (contest slips) ----------
# House keeps ~12% (win prob = 0.88 / multiplier). Gentle multiplier ladder
# keeps revenue variance realistic. Retained players stay active ~40 days and
# play far more; churned players stop by ~day 14.
tier_ent = {'low': 3, 'mid': 12, 'high': 30}
mult = {2: 2.5, 3: 4, 4: 6, 5: 9, 6: 13}
HOLD = 0.12
ent_rows = []
for i, row in players.iterrows():
    if retained_30[i]:
        count = tier_ent[row.value_tier] * 4.0
        day_hi = 40
    else:
        count = tier_ent[row.value_tier] * 0.6
        day_hi = 14
    n_ent = rng.poisson(count)
    for _ in range(int(n_ent)):
        day = rng.integers(0, day_hi)
        fee = round(float(rng.choice([5, 10, 20, 25, 50],
                     p=[.4, .3, .15, .1, .05])), 2)
        picks = int(rng.choice([2, 3, 4, 5, 6], p=[.40, .34, .16, .07, .03]))
        m = mult[picks]
        win = rng.random() < ((1 - HOLD) / m)
        payout = round(fee * m, 2) if win else 0.0
        ent_rows.append((row.player_id,
                         row.signup_date + timedelta(days=int(day)),
                         fee, picks, int(win), payout))
entries = pd.DataFrame(ent_rows, columns=['player_id', 'entry_date',
          'entry_fee', 'num_picks', 'won', 'payout'])
entries.insert(0, 'entry_id', np.arange(1, len(entries) + 1))

# ---------- write CSVs + SQLite ----------
os.makedirs('data', exist_ok=True)
players.to_csv('data/players.csv', index=False)
deposits.to_csv('data/deposits.csv', index=False)
entries.to_csv('data/entries.csv', index=False)
bonus.to_csv('data/bonus.csv', index=False)
con = sqlite3.connect('data/prizepicks.db')
players.to_sql('players', con, if_exists='replace', index=False)
deposits.to_sql('deposits', con, if_exists='replace', index=False)
entries.to_sql('entries', con, if_exists='replace', index=False)
bonus.to_sql('bonus', con, if_exists='replace', index=False)
con.close()
print('Done. Players:', len(players), '| Deposits:', len(deposits),
      '| Entries:', len(entries))