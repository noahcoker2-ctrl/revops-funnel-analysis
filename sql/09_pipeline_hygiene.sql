-- Open deals that make the forecast less reliable, by AE:
--   past due  = expected close date already passed
--   stale     = no stage change in 30+ days
--   pushed 2+ = close date moved out at least twice
SELECT
  ow.owner_name                                                     AS ae,
  count(*)                                                          AS open_deals,
  count(*) FILTER (WHERE o.close_date < as_of())                    AS past_due,
  count(*) FILTER (WHERE o.last_stage_change_at < as_of() - INTERVAL 30 DAY) AS stale_30d,
  count(*) FILTER (WHERE o.close_date_pushes >= 2)                  AS pushed_twice_or_more,
  sum(o.amount)                                                     AS open_pipeline,
  coalesce(sum(o.amount) FILTER (WHERE o.close_date < as_of()
                                    OR o.last_stage_change_at < as_of() - INTERVAL 30 DAY
                                    OR o.close_date_pushes >= 2), 0) AS at_risk_pipeline,
  round(coalesce(sum(o.amount) FILTER (WHERE o.close_date < as_of()
                                          OR o.last_stage_change_at < as_of() - INTERVAL 30 DAY
                                          OR o.close_date_pushes >= 2), 0) / sum(o.amount), 3) AS at_risk_share
FROM opportunities o
JOIN owners ow USING (owner_id)
WHERE NOT o.is_closed
GROUP BY 1
ORDER BY at_risk_pipeline DESC;
