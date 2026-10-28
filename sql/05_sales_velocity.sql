-- Sales velocity by segment over the last four full quarters (2025-Q4 to 2026-Q3).
--   velocity ($ per day) = opportunities per quarter x win rate x average won deal / average sales cycle (days)
-- It's the classic formula, useful for comparing segments and tracking the four levers over time.
-- It is not a revenue forecast, so actual won ACV per quarter is shown next to it for context.
WITH created AS (
  SELECT segment, count(*) / 4.0 AS opps_per_quarter
  FROM opportunities
  WHERE created_at::DATE BETWEEN DATE '2025-10-01' AND DATE '2026-09-30'
  GROUP BY 1
),
closed AS (
  SELECT
    segment,
    count(*) FILTER (WHERE is_won) / count(*)                       AS win_rate,
    avg(amount) FILTER (WHERE is_won)                               AS avg_won_acv,
    avg(date_diff('day', created_at::DATE, close_date)) FILTER (WHERE is_won) AS avg_cycle_days,
    sum(amount) FILTER (WHERE is_won) / 4.0                         AS won_acv_per_quarter
  FROM opportunities
  WHERE is_closed AND close_date BETWEEN DATE '2025-10-01' AND DATE '2026-09-30'
  GROUP BY 1
)
SELECT
  segment,
  round(opps_per_quarter, 1)                                        AS opps_per_quarter,
  round(win_rate, 3)                                                AS win_rate,
  round(avg_won_acv)                                                AS avg_won_acv,
  round(avg_cycle_days, 1)                                          AS avg_cycle_days,
  round(opps_per_quarter * win_rate * avg_won_acv / avg_cycle_days) AS velocity_per_day,
  round(won_acv_per_quarter)                                        AS actual_won_acv_per_quarter
FROM created JOIN closed USING (segment)
ORDER BY segment_order(segment);
