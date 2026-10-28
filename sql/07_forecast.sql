-- 2026-Q4 forecast by region, two ways:
--   Fixed default: open pipeline x a common fixed set of stage probabilities (10/25/50/75%)
--   Historical:   open pipeline x the share of past deals in that stage and segment that were won
-- Both add the revenue already won this quarter.
WITH stage_history AS (  -- every closed deal and the stages it passed through
  SELECT DISTINCT h.opportunity_id, h.stage, o.segment, o.is_won
  FROM opportunity_stage_history h
  JOIN opportunities o USING (opportunity_id)
  WHERE o.is_closed AND h.stage IN ('Discovery', 'Demo', 'Proposal', 'Negotiation')
    AND o.close_date >= as_of() - INTERVAL 365 DAY
),
historical AS (
  SELECT segment, stage, avg(CASE WHEN is_won THEN 1.0 ELSE 0.0 END) AS p_win, count(*) AS deals
  FROM stage_history GROUP BY ALL
),
fixed_default AS (
  SELECT * FROM (VALUES ('Discovery', 0.10), ('Demo', 0.25), ('Proposal', 0.50), ('Negotiation', 0.75)) t(stage, p_win)
),
open_q4 AS (
  SELECT o.*
  FROM opportunities o
  WHERE NOT o.is_closed AND o.close_date BETWEEN DATE '2026-10-01' AND DATE '2026-12-31'
),
won_q4 AS (
  SELECT region, sum(amount) AS won FROM opportunities
  WHERE is_won AND close_date BETWEEN DATE '2026-10-01' AND DATE '2026-12-31' GROUP BY 1
),
quota_q4 AS (
  SELECT ow.region, sum(qu.quota) AS quota FROM quotas qu JOIN owners ow USING (owner_id)
  WHERE qu.quarter = '2026Q4' GROUP BY 1
),
weighted AS (
  SELECT
    o.region,
    sum(o.amount)                    AS open_pipeline,
    sum(o.amount * d.p_win)          AS fixed_weighted,
    sum(o.amount * h.p_win)          AS historical_weighted
  FROM open_q4 o
  JOIN fixed_default d USING (stage)
  JOIN historical h ON h.segment = o.segment AND h.stage = o.stage
  GROUP BY 1
)
SELECT
  q.region,
  q.quota,
  coalesce(w.won, 0)                                                AS won_to_date,
  round(p.open_pipeline)                                            AS open_pipeline,
  round(coalesce(w.won, 0) + p.fixed_weighted)                        AS forecast_fixed_default,
  round(coalesce(w.won, 0) + p.historical_weighted)                 AS forecast_historical,
  round((coalesce(w.won, 0) + p.fixed_weighted) / q.quota, 3)         AS attainment_fixed_default,
  round((coalesce(w.won, 0) + p.historical_weighted) / q.quota, 3)  AS attainment_historical,
  round(p.historical_weighted - p.fixed_weighted)                     AS historical_minus_fixed
FROM quota_q4 q
LEFT JOIN won_q4 w USING (region)
LEFT JOIN weighted p USING (region)
ORDER BY q.region;
