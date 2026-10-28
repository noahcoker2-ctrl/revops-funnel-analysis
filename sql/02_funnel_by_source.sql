-- Which lead sources turn into revenue? Conversion at each step, win rate and deal size.
SELECT
  l.source,
  count(*)                                                          AS leads,
  round(count(l.mql_at) / count(*), 3)                              AS lead_to_mql,
  round(count(l.sql_at) / nullif(count(l.mql_at), 0), 3)            AS mql_to_sql,
  round(count(l.opportunity_id) / count(*), 3)                      AS lead_to_opp,
  count(*) FILTER (WHERE o.is_closed)                               AS closed_opps,
  round(count(*) FILTER (WHERE o.is_won)
        / nullif(count(*) FILTER (WHERE o.is_closed), 0), 3)        AS win_rate,
  round(avg(o.amount) FILTER (WHERE o.is_won))                      AS avg_won_acv,
  sum(o.amount) FILTER (WHERE o.is_won)                             AS won_acv,
  round(sum(o.amount) FILTER (WHERE o.is_won) / count(*))           AS won_acv_per_lead
FROM leads l
LEFT JOIN opportunities o USING (opportunity_id)
GROUP BY 1
ORDER BY won_acv DESC;
