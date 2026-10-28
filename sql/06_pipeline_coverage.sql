-- Pipeline coverage for this quarter (2026-Q4) and next (2027-Q1), by region.
-- coverage = open pipeline expected to close in the quarter / quota still to win.
-- Rule of thumb: 3x for the current quarter is healthy; under 2x is a warning.
-- "Clean" coverage leaves out deals that are past due, stale (no stage change in 30+ days)
-- or pushed twice or more, because those rarely close on time.
WITH q AS (
  SELECT * FROM (VALUES ('2026-Q4', DATE '2026-10-01', DATE '2026-12-31'),
                        ('2027-Q1', DATE '2027-01-01', DATE '2027-03-31')) t(quarter, q_start, q_end)
),
quota AS (
  SELECT qu.quarter, ow.region, sum(qu.quota) AS quota
  FROM quotas qu JOIN owners ow USING (owner_id)
  WHERE qu.quarter IN ('2026Q4', '2027Q1')
  GROUP BY ALL
),
won AS (
  SELECT q.quarter, o.region, sum(o.amount) AS won_qtd
  FROM opportunities o JOIN q ON o.close_date BETWEEN q.q_start AND q.q_end
  WHERE o.is_won
  GROUP BY ALL
),
pipe AS (
  SELECT
    q.quarter, o.region,
    sum(o.amount) AS open_pipeline,
    count(*) AS open_deals,
    sum(o.amount) FILTER (WHERE NOT (o.close_date < as_of()
                                     OR o.last_stage_change_at < as_of() - INTERVAL 30 DAY
                                     OR o.close_date_pushes >= 2)) AS clean_pipeline
  FROM opportunities o JOIN q ON o.close_date BETWEEN q.q_start AND q.q_end
  WHERE NOT o.is_closed
  GROUP BY ALL
)
SELECT
  q.quarter,
  r.region,
  qt.quota,
  coalesce(w.won_qtd, 0)                                            AS won_to_date,
  qt.quota - coalesce(w.won_qtd, 0)                                 AS quota_remaining,
  coalesce(p.open_pipeline, 0)                                      AS open_pipeline,
  coalesce(p.open_deals, 0)                                         AS open_deals,
  round(coalesce(p.open_pipeline, 0) / nullif(qt.quota - coalesce(w.won_qtd, 0), 0), 2) AS coverage,
  coalesce(p.clean_pipeline, 0)                                     AS clean_pipeline,
  round(coalesce(p.clean_pipeline, 0) / nullif(qt.quota - coalesce(w.won_qtd, 0), 0), 2) AS clean_coverage
FROM q
CROSS JOIN (SELECT DISTINCT region FROM owners WHERE role = 'AE') r
JOIN quota qt ON qt.quarter = replace(q.quarter, '-', '') AND qt.region = r.region
LEFT JOIN won w ON w.quarter = q.quarter AND w.region = r.region
LEFT JOIN pipe p ON p.quarter = q.quarter AND p.region = r.region
ORDER BY q.quarter, r.region;
