# Reinvestment ROI — Player Retention & A/B Testing Analysis

**Built to mirror the PrizePicks Revenue Operations function | Daily Fantasy Sports retention economics**

> An end-to-end analytics project that answers the single question this role owns: *is our reinvestment-bonus spend actually buying retention and revenue — and for which players is it worth it?* Player segmentation in SQL, a properly designed A/B test on a deposit-match bonus, a Tableau leadership dashboard, and a segmented spend recommendation.

---

## Business Problem

PrizePicks spends real money to keep players active — deposit-match bonuses, free entries, and promos. Revenue Operations calls this **reinvestment spend**. Leadership needs an analyst to answer:

- Does the reinvestment bonus actually **lift retention** versus players who don't receive it?
- Does the bonus **pay for itself** — is the incremental net revenue larger than the bonus cost (positive ROI)?
- **Which player segments** should the spend be concentrated on, and which should it be pulled from?
- How do early player behaviors (deposits, contest entries) roll up into the business KPIs leadership tracks — retention, ARPU, net gaming revenue, and reinvestment ROI?

This project builds a complete analytics pipeline answering those questions on a dataset modeled directly on the PrizePicks DFS revenue model: players, deposits, contest entries, and a randomized reinvestment-bonus experiment.

---

## Why This Data Is Simulated

PrizePicks' retention, deposit, and reinvestment data is internal and proprietary — no Daily Fantasy Sports company publishes player-level revenue or A/B test data, and there is no public PrizePicks API for it. The only PrizePicks data reachable publicly is current projection lines (today's player props), which contain no retention, revenue, or player information and cannot answer this project's question.

So this project uses a **synthetic dataset modeled on the PrizePicks economics**, generated reproducibly in Python (`seed=42`): players, deposits, contest entries (entry fees minus payouts), and a randomized reinvestment-bonus experiment. Building it required modeling how a DFS book actually earns and how player value drives behavior — which is the point. None of the analysis code knows the "ground truth" baked into the generator; the SQL and the A/B test have to *discover* it, exactly like real analysis.

**The same SQL and A/B framework drops directly onto equivalent internal tables — only the data source changes.**

> **Interview line:** *"PrizePicks' retention and reinvestment data is internal — no DFS company publishes that. So I modeled a dataset on the actual PrizePicks economics so I could demonstrate the exact retention and reinvestment workflows this role owns. The framework drops straight onto the real internal tables on day one."*

---

## Architecture

```
Python generator (01_generate_data.py)
   → 4 modeled tables: players · deposits · entries · bonus
   → written to CSV + SQLite (data/prizepicks.db)
        → SQL analysis (02_analysis.sql)
             RFM segmentation · retention cohorts · running LTV · net revenue by segment
        → A/B test (03_ab_test.py)
             two-proportion z-test (retention) · Welch t-test (revenue) · ROI by segment
                 → Tableau Public dashboard (4 tiles, leadership-ready)
                      → README + 1-slide executive readout + recommendation
```

---

## Key Findings

> Numbers below are from the reproducible run (`seed=42`, ~3,700 players per group). Re-run `03_ab_test.py` to confirm them on your machine.

1. **Retention lift is large and highly significant.** The reinvestment bonus raised 30-day retention from **27.6%** (control) to **34.5%** (treatment) — a **+6.9 pt** lift, significant at α = 0.05 (two-proportion z-test, *p* < 0.001, statistical power ≈ 1.0). This is the rock-solid headline.
2. **The program is modestly ROI-positive overall.** Across all treated players, **$17,318** in bonus spend generated roughly **$18,977** in incremental 30-day net revenue — a program ROI of about **+10%**. (Net revenue per player: $25.81 treatment vs $20.72 control, *p* = 0.07 — directional, and a good example of a revenue effect being harder to power than a retention effect.)
3. **The average hides the real story — this is the headline insight.** ROI by player value tier:
   - **Mid-value players: strongly ROI-positive (+66%)** — the bonus clearly pays for itself here.
   - **Low-value players: deeply ROI-negative (−132%)** — they take the bonus but barely change behavior. Near-pure cost.
   - **High-value players: ROI-negative at 30 days (−44%)** — they *do* retain more, but they already retain well without a bonus, so the marginal spend is largely wasted on this horizon.
4. **Recommendation:** Concentrate reinvestment spend on **mid-value players**, where payback is clear and positive. **Stop bonusing low-value players** — it's almost entirely waste. For **high-value players**, don't judge on 30-day ROI; they retain well regardless, so evaluate the bonus against **lifetime value over a longer horizon** before scaling.

---

## A/B Test Methodology

| Element | Definition |
|---|---|
| **Question** | Does a 15% first-deposit reinvestment bonus (capped at $12) increase 30-day retention and net revenue enough to justify its cost? |
| **Population** | New players who signed up during a ~6-week enrollment window (signup days 15–59) |
| **Assignment** | Randomized 50/50 — treatment (received bonus) vs control (no bonus) |
| **Primary metric** | 30-day retention (a proportion) → **two-proportion z-test** |
| **Secondary metric** | 30-day net revenue per player (a mean) → **Welch's t-test** |
| **Guardrail / decision metric** | Reinvestment ROI = (incremental net revenue − bonus spend) / bonus spend |
| **Hypotheses** | H₀: retention is equal across groups. H₁: treatment retention is higher. |
| **Significance level** | α = 0.05 |
| **Validity checks** | Wilson confidence intervals on each rate; post-hoc statistical power; segment cut by value tier to test for heterogeneous treatment effects |

---

## Data Quality & Modeling Notes

- **Reproducibility:** the entire dataset is regenerated deterministically from `seed=42` — anyone can rerun `01_generate_data.py` and get identical results.
- **Retention is defined behaviorally**, not by login: a player is "retained at 30 days" if they placed at least one contest entry between day 23 and day 37 after signup — an observable proxy, not the hidden generator flag.
- **Net revenue = entry fees collected − payouts**, computed per player over the first 30 days, mirroring net gaming revenue.
- **Bonus cost is tracked explicitly** (15% match, $12 cap, first deposit only) so ROI is measured against real spend, not assumed.
- **Modeled population:** 20,000 players, 75,370 deposits, and 357,695 contest entries across value tiers (low / mid / high).

---

## Tech Stack

| Component | Tool |
|---|---|
| Data generation | Python 3.10+ (pandas, numpy) |
| Database / query | SQLite via DB Browser for SQLite |
| SQL techniques | CTEs, window functions (`NTILE`, `ROW_NUMBER`, `LAG`, windowed `SUM`) |
| A/B testing | Python (scipy, statsmodels) |
| Visualization | Tableau Public |
| Deliverables | GitHub repo · executive slide · written recommendation |

---

## Dashboard

**Live dashboard:** https://public.tableau.com/app/profile/benjamin.agee/viz/PrizePicksReinvestmentROI/ReinvestmentROIWhereBonusSpendPaysBack

Four leadership tiles, one question each:

1. **Retention cohort curve** — retention decay by signup week.
2. **Net revenue by segment** — where the money actually comes from.
3. **A/B retention lift by tier** — treatment vs control, the mid-tier gap pops.
4. **Reinvestment ROI by tier** — the punchline; low tier red (negative), mid/high green.

```
![Dashboard — Reinvestment ROI](tableau/dashboard.png)
```

---

## Repository Structure

```
prizepicks-reinvestment-roi/
  python/
    01_generate_data.py     # builds the modeled DFS dataset → CSV + SQLite
    03_ab_test.py           # retention z-test, revenue t-test, ROI by tier
  sql/
    02_analysis.sql         # RFM segmentation, cohorts, running LTV, net revenue
  tableau/
    dashboard.png           # dashboard screenshot + link in README
  slides/
    executive_readout.pdf   # one-slide recommendation for leadership
  data/                     # generated CSVs + prizepicks.db (git-ignored)
  README.md
  .gitignore
```

---

## How to Reproduce

1. `git clone https://github.com/YOURUSERNAME/prizepicks-reinvestment-roi`
2. Install Python 3.10+, then: `pip install pandas numpy scipy statsmodels`
3. Generate the data: `python python/01_generate_data.py`
   *(creates `data/prizepicks.db` and the CSV exports; prints row counts)*
4. Open `data/prizepicks.db` in **DB Browser for SQLite** and run the queries in `sql/02_analysis.sql` (Execute SQL tab). Export the result grids to CSV for Tableau.
5. Run the experiment: `python python/03_ab_test.py`
   *(prints retention lift + p-value, revenue test, overall ROI, and ROI by value tier)*
6. Open **Tableau Public** → connect to the exported CSVs → build the four tiles → publish and paste the link above.

---

## Dataset

Synthetic dataset modeled on the PrizePicks Daily Fantasy Sports revenue model (deposits, contest entries, deposit-match reinvestment bonus). Generated reproducibly in `python/01_generate_data.py` (`seed=42`). No real or proprietary PrizePicks data is used — the framework is built to drop directly onto equivalent internal tables.

---

## What I'd Do With Real PrizePicks Data

- **Pre-register the test plan** (metrics, sample size, stopping rule) before launch to avoid peeking bias.
- **Extend the horizon** beyond 30 days to capture longer payback and true LTV, not just early revenue.
- **Add sequential monitoring** with corrected error rates so the test can be stopped early without inflating false positives.
- **Track a guardrail** like deposit frequency and responsible-play signals to ensure retention gains aren't coming from unhealthy behavior.
- **Hold out a permanent control** to measure the long-run incrementality of the reinvestment program as a whole.
