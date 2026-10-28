-- AE scorecard for the last four full quarters (2025-Q4 to 2026-Q3).
WITH deals AS (
  SELECT * FROM opportunities
  WHERE is_closed AND close_date BETWEEN DATE '2025-10-01' AND DATE '2026-09-30'
),
quota AS (
  SELECT owner_id, sum(quota) AS quota FROM quotas
  WHERE quarter IN ('2025Q4', '2026Q1', '2026Q2', '2026Q3') GROUP BY 1
),
proposal_days AS (
  SELECT o.owner_id, median(date_diff('minute', h.entered_at, h.exited_at) / 1440.0) AS median_days_in_proposal
  FROM opportunity_stage_history h JOIN opportunities o USING (opportunity_id)
  WHERE h.stage = 'Proposal' AND h.exited_at::DATE BETWEEN DATE '2025-10-01' AND DATE '2026-09-30'
  GROUP BY 1
),
open_now AS (
  SELECT owner_id, sum(amount) AS open_pipeline, count(*) AS open_deals
  FROM opportunities WHERE NOT is_closed GROUP BY 1
)
SELECT
  ow.owner_name                                                     AS ae,
  ow.segment,
  ow.region,
  q.quota,
  coalesce(sum(d.amount) FILTER (WHERE d.is_won), 0)                AS won_acv,
  round(coalesce(sum(d.amount) FILTER (WHERE d.is_won), 0) / q.quota, 3) AS attainment,
  count(d.opportunity_id)                                           AS closed_deals,
  round(count(*) FILTER (WHERE d.is_won) / nullif(count(d.opportunity_id), 0), 3) AS win_rate,
  round(avg(d.amount) FILTER (WHERE d.is_won))                      AS avg_won_acv,
  round(pd.median_days_in_proposal, 1)                              AS median_days_in_proposal,
  coalesce(n.open_deals, 0)                                         AS open_deals,
  coalesce(n.open_pipeline, 0)                                      AS open_pipeline
FROM owners ow
JOIN quota q USING (owner_id)
LEFT JOIN deals d USING (owner_id)
LEFT JOIN proposal_days pd USING (owner_id)
LEFT JOIN open_now n USING (owner_id)
WHERE ow.role = 'AE'
GROUP BY ow.owner_name, ow.segment, ow.region, q.quota, pd.median_days_in_proposal, n.open_deals, n.open_pipeline
ORDER BY attainment DESC;
