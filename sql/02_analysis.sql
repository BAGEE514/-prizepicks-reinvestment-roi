-- ============================================================
-- Phase 2 - SQL Analysis  |  Reinvestment ROI (PrizePicks)
-- Run each query in DB Browser for SQLite -> Execute SQL tab.
-- Highlight ONE query at a time and click Run (Ctrl+Enter) so the
-- results grid shows that query's output, then export it to CSV.
-- ============================================================


-- ------------------------------------------------------------
-- 2.1  RFM SEGMENTATION   (CTEs + NTILE window function)
-- Scores every player on Recency, Frequency, Monetary value and
-- buckets them into VIP / Core / Casual / At-Risk.
-- Export the result as:  data/seg_rfm.csv
-- ------------------------------------------------------------
WITH activity AS (
  SELECT p.player_id, p.value_tier, p.acquisition_channel,
         MAX(e.entry_date)            AS last_entry,
         COUNT(e.entry_id)            AS freq,
         COALESCE(SUM(e.entry_fee),0) AS monetary
  FROM players p
  LEFT JOIN entries e ON e.player_id = p.player_id
  GROUP BY p.player_id, p.value_tier, p.acquisition_channel
),
scored AS (
  SELECT *,
    NTILE(5) OVER (ORDER BY julianday(last_entry)) AS r_score,
    NTILE(5) OVER (ORDER BY freq)                  AS f_score,
    NTILE(5) OVER (ORDER BY monetary)              AS m_score
  FROM activity
)
SELECT player_id, value_tier, freq, monetary,
       r_score, f_score, m_score,
       (r_score + f_score + m_score) AS rfm_total,
       CASE WHEN (r_score + f_score + m_score) >= 12 THEN 'VIP'
            WHEN (r_score + f_score + m_score) >=  8 THEN 'Core'
            WHEN (r_score + f_score + m_score) >=  5 THEN 'Casual'
            ELSE 'At-Risk' END AS rfm_segment
FROM scored
ORDER BY rfm_total DESC;


-- ------------------------------------------------------------
-- 2.2  WEEKLY RETENTION COHORTS   (CTEs + date math)
-- Groups players by signup week and measures the share still
-- entering contests 1 week and 4 weeks later.
-- Export the result as:  data/cohorts.csv
-- ------------------------------------------------------------
WITH base AS (
  SELECT player_id,
         strftime('%Y-%W', signup_date) AS cohort_week,
         signup_date
  FROM players
),
acts AS (
  SELECT b.player_id, b.cohort_week,
         CAST((julianday(e.entry_date) - julianday(b.signup_date)) / 7 AS INT)
           AS week_since_signup
  FROM base b
  JOIN entries e ON e.player_id = b.player_id
)
SELECT cohort_week,
       COUNT(DISTINCT player_id) AS cohort_size,
       COUNT(DISTINCT CASE WHEN week_since_signup = 1 THEN player_id END) * 1.0
         / COUNT(DISTINCT player_id) AS wk1_retention,
       COUNT(DISTINCT CASE WHEN week_since_signup = 4 THEN player_id END) * 1.0
         / COUNT(DISTINCT player_id) AS wk4_retention
FROM acts
GROUP BY cohort_week
ORDER BY cohort_week;


-- ------------------------------------------------------------
-- 2.3  PLAYER LTV WITH RUNNING TOTAL  (SUM OVER + LAG + ROW_NUMBER)
-- A windowed running sum of deposits per player, plus the change
-- versus the previous deposit. Inspect a few players.
-- (No export needed - this one demonstrates window functions.)
-- ------------------------------------------------------------
WITH dep AS (
  SELECT player_id, deposit_date, amount,
         SUM(amount) OVER (PARTITION BY player_id
                           ORDER BY deposit_date
                           ROWS BETWEEN UNBOUNDED PRECEDING
                           AND CURRENT ROW)            AS running_deposits,
         amount - LAG(amount) OVER (PARTITION BY player_id
                           ORDER BY deposit_date)      AS delta_vs_prev,
         ROW_NUMBER() OVER (PARTITION BY player_id
                           ORDER BY deposit_date)      AS deposit_seq
  FROM deposits
)
SELECT player_id, deposit_seq, deposit_date, amount,
       running_deposits, delta_vs_prev
FROM dep
WHERE player_id IN (1, 2, 3)
ORDER BY player_id, deposit_seq;


-- ------------------------------------------------------------
-- 2.4  NET GAMING REVENUE BY SEGMENT   (the KPI roll-up)
-- Net revenue = entry fees collected minus payouts, by tier + channel.
-- Export the result as:  data/net_rev.csv
-- ------------------------------------------------------------
SELECT p.value_tier,
       p.acquisition_channel,
       COUNT(DISTINCT p.player_id)                   AS players,
       ROUND(SUM(e.entry_fee), 2)                    AS gross_wagered,
       ROUND(SUM(e.payout), 2)                       AS total_payouts,
       ROUND(SUM(e.entry_fee) - SUM(e.payout), 2)    AS net_revenue,
       ROUND((SUM(e.entry_fee) - SUM(e.payout)) * 1.0
             / COUNT(DISTINCT p.player_id), 2)        AS net_rev_per_player
FROM players p
JOIN entries e ON e.player_id = p.player_id
GROUP BY p.value_tier, p.acquisition_channel
ORDER BY net_revenue DESC;