-- Outbound pipeline created per month by region, next to active SDR headcount.
-- Shows what happens to pipeline when an SDR seat sits empty.
WITH months AS (
  SELECT unnest(generate_series(DATE '2026-01-01', DATE '2026-10-01', INTERVAL 1 MONTH))::DATE AS month
),
sdrs AS (
  SELECT m.month, ow.region, count(*) AS active_sdrs
  FROM months m JOIN owners ow
    ON ow.role = 'SDR' AND ow.start_date <= m.month AND (ow.end_date IS NULL OR ow.end_date >= m.month)
  GROUP BY ALL
),
pipe AS (
  SELECT date_trunc('month', created_at)::DATE AS month, region,
         count(*) AS outbound_opps, sum(amount) AS outbound_pipeline
  FROM opportunities
  WHERE source = 'Outbound' AND created_at >= DATE '2026-01-01'
  GROUP BY ALL
)
SELECT s.month, s.region, s.active_sdrs,
       coalesce(p.outbound_opps, 0) AS outbound_opps,
       coalesce(p.outbound_pipeline, 0) AS outbound_pipeline
FROM sdrs s LEFT JOIN pipe p USING (month, region)
ORDER BY s.region, s.month;
