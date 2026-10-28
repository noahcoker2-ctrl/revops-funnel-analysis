-- Win rate and sales cycle by segment and source (all closed deals).
SELECT
  segment,
  source,
  count(*)                                                          AS closed_deals,
  count(*) FILTER (WHERE is_won)                                    AS won,
  round(count(*) FILTER (WHERE is_won) / count(*), 3)               AS win_rate,
  round(sum(amount) FILTER (WHERE is_won) / sum(amount), 3)         AS value_win_rate,
  round(avg(amount) FILTER (WHERE is_won))                          AS avg_won_acv,
  round(median(date_diff('day', created_at::DATE, close_date)) FILTER (WHERE is_won)) AS median_cycle_days_won
FROM opportunities
WHERE is_closed
GROUP BY segment, source
ORDER BY segment_order(segment), win_rate DESC;
