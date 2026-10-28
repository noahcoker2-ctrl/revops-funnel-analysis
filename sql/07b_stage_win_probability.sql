-- Historical chance of winning from each stage (deals closed in the last 12 months),
-- next to a common fixed set of stage probabilities (10/25/50/75%).
WITH stage_history AS (
  SELECT DISTINCT h.opportunity_id, h.stage, o.segment, o.is_won
  FROM opportunity_stage_history h
  JOIN opportunities o USING (opportunity_id)
  WHERE o.is_closed AND h.stage IN ('Discovery', 'Demo', 'Proposal', 'Negotiation')
    AND o.close_date >= as_of() - INTERVAL 365 DAY
)
SELECT
  segment,
  stage,
  count(*)                                                          AS closed_deals_that_reached_stage,
  round(avg(CASE WHEN is_won THEN 1.0 ELSE 0.0 END), 3)             AS historical_p_win,
  CASE stage WHEN 'Discovery' THEN 0.10 WHEN 'Demo' THEN 0.25
             WHEN 'Proposal' THEN 0.50 WHEN 'Negotiation' THEN 0.75 END AS fixed_default_p_win
FROM stage_history
GROUP BY segment, stage
ORDER BY segment_order(segment), stage_order(stage);
