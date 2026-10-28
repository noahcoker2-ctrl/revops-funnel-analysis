-- Why we lose, by the stage the deal died in.
WITH lost AS (
  SELECT o.*, h.stage AS lost_at_stage
  FROM opportunities o
  JOIN opportunity_stage_history h USING (opportunity_id)
  WHERE o.stage = 'Closed Lost'
  QUALIFY row_number() OVER (PARTITION BY o.opportunity_id ORDER BY h.entered_at DESC) = 2
)
SELECT
  lost_at_stage,
  lost_reason,
  count(*)                                                          AS deals,
  sum(amount)                                                       AS lost_acv,
  round(count(*) / sum(count(*)) OVER (PARTITION BY lost_at_stage), 3) AS share_of_stage_losses
FROM lost
GROUP BY lost_at_stage, lost_reason
ORDER BY stage_order(lost_at_stage), deals DESC;
