-- Where do deals stall or die? For every stage: how many deals reached it,
-- what share moved on (of those that left the stage), and how long they sat there.
WITH h AS (
  SELECT
    h.*,
    o.segment,
    lead(h.stage) OVER (PARTITION BY h.opportunity_id ORDER BY h.entered_at) AS next_stage
  FROM opportunity_stage_history h
  JOIN opportunities o USING (opportunity_id)
)
SELECT
  segment,
  stage,
  count(*)                                                          AS reached,
  count(*) FILTER (WHERE exited_at IS NOT NULL)                     AS left_stage,
  count(*) FILTER (WHERE exited_at IS NULL)                         AS still_open_here,
  round(avg(CASE WHEN next_stage <> 'Closed Lost' THEN 1.0 ELSE 0.0 END)
        FILTER (WHERE exited_at IS NOT NULL), 3)                    AS advance_rate,
  round(median(date_diff('minute', entered_at, exited_at) / 1440.0)
        FILTER (WHERE exited_at IS NOT NULL), 1)                    AS median_days_in_stage,
  round(quantile_cont(date_diff('minute', entered_at, exited_at) / 1440.0, 0.9)
        FILTER (WHERE exited_at IS NOT NULL), 1)                    AS p90_days_in_stage
FROM h
WHERE stage IN ('Discovery', 'Demo', 'Proposal', 'Negotiation')
GROUP BY segment, stage
ORDER BY segment_order(segment), stage_order(stage);
