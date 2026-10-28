-- Lead-to-win funnel by the quarter the lead came in.
-- Recent quarters are still maturing: their opportunities haven't all closed yet,
-- so win rate here is won / closed, not won / created.
SELECT
  qlabel(l.created_at)                                              AS lead_quarter,
  count(*)                                                          AS leads,
  count(l.mql_at)                                                   AS mqls,
  count(l.sql_at)                                                   AS sqls,
  count(l.opportunity_id)                                           AS opportunities,
  count(*) FILTER (WHERE o.is_won)                                  AS won,
  round(count(l.mql_at) / count(*), 3)                              AS lead_to_mql,
  round(count(l.sql_at) / nullif(count(l.mql_at), 0), 3)            AS mql_to_sql,
  round(count(l.opportunity_id) / nullif(count(l.sql_at), 0), 3)    AS sql_to_opp,
  round(count(*) FILTER (WHERE o.is_won)
        / nullif(count(*) FILTER (WHERE o.is_closed), 0), 3)        AS win_rate_of_closed,
  round(count(*) FILTER (WHERE o.is_closed)
        / nullif(count(l.opportunity_id), 0), 3)                    AS share_of_opps_closed
FROM leads l
LEFT JOIN opportunities o USING (opportunity_id)
GROUP BY 1
ORDER BY 1;
