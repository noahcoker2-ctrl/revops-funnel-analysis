# Rebuild the dashboard in Looker Studio

About 45 minutes. You'll end up with a shareable, interactive dashboard with the same numbers as this repo.

## 1. Get the data into Google

Pick one path.

**A. Google Sheets (fastest).** Create a Google Sheet called `RevOps funnel results` and import each file in `results/` as its own tab (File > Import > Upload > "Insert new sheet"). Name each tab after the file, for example `06_pipeline_coverage`.

**B. BigQuery (more realistic, still free in the sandbox).** Create a dataset `revops`, load the six files in `data/` as tables, then save each query in `sql/` as a view. The queries are written for DuckDB, so expect to rework each one. The main changes:

| DuckDB (this repo) | BigQuery |
|---|---|
| `read_csv_auto(...)` in `00_load.sql` | load the CSVs as tables instead |
| `count(*) FILTER (WHERE x)` | `COUNTIF(x)` |
| `sum(amount) FILTER (WHERE x)` | `SUM(IF(x, amount, 0))` |
| `avg(x) FILTER (WHERE c)`, `median(x) FILTER (WHERE c)` | `AVG(IF(c, x, NULL))`, `APPROX_QUANTILES(IF(c, x, NULL), 2)[OFFSET(1)]` |
| `quantile_cont(x, 0.9)` | `APPROX_QUANTILES(x, 10)[OFFSET(9)]` |
| `date_diff('day', a, b)` on dates | `DATE_DIFF(b, a, DAY)` |
| `date_diff('minute', a, b)` on timestamps | `TIMESTAMP_DIFF(b, a, MINUTE)` |
| `date_trunc('month', ts)` | `TIMESTAMP_TRUNC(ts, MONTH)` (part comes second) |
| `x::DATE` | `DATE(x)` |
| `VALUES (...) t(col1, col2)` | `SELECT ... UNION ALL SELECT ...`, or an `UNNEST` of structs |
| `generate_series(...)` | `GENERATE_DATE_ARRAY(...)` |
| `as_of()` macro | `DATE '2026-10-27'` |
| `qlabel(ts)` macro | `FORMAT_DATE('%Y-Q%Q', DATE(ts))` |
| `stage_order()` / `segment_order()` macros | the same `CASE` expression written inline |
| `GROUP BY ALL` | list the columns |

`QUALIFY` works in BigQuery as it is.

## 2. Connect Looker Studio

lookerstudio.google.com > Create > Report > add one data source per tab or view. Set number formats as you connect:

- `win_rate`, `advance_rate`, `attainment`, `historical_p_win`, `fixed_default_p_win`: Percent
- `won_acv`, `open_pipeline`, `clean_pipeline`, `quota`, `won_to_date` and the other money fields: Currency (USD)
- `coverage`, `clean_coverage`: Number with 2 decimals

## 3. Build the pages

Use one page per question, with a title, one sentence of takeaway, then the charts.

**Page 1: Executive summary**
- Scorecards: Q4 clean coverage per region (`06`, filter quarter = 2026-Q4), forecast attainment with historical rates (`07`), and overall win rate as a calculated field on `04`: `SUM(won) / SUM(closed_deals)`. Don't average the `win_rate` column, because that weights a small source the same as a large one.
- Bar chart: reported vs clean coverage by region (`06`), with a reference line at 3.

**Page 2: Funnel and sources**
- Table with heatmap: `01_funnel_by_quarter`, conversion columns shaded.
- Bar chart: win rate by source (`02`), sorted descending.
- Bar chart: won ACV per lead by source (`02`).

**Page 3: Where deals stall**
- Grouped bar: median days in stage by stage, broken down by segment (`03`).
- Bar: advance rate by stage, with a segment filter control (`03`).
- Stacked bar: lost reasons by stage (`10`).

**Page 4: Forecast**
- Grouped bar: fixed default vs historical win probability by stage, with a segment filter (`07b`).
- Table: forecast by region, both methods, with attainment (`07`).

**Page 5: Team**
- Bar: attainment by AE with a reference line at 100% (`08`).
- Table: AE scorecard (`08`) next to hygiene (`09`), with conditional formatting on `at_risk_share` above 50%.
- Column chart: EMEA outbound pipeline by month (`11`, filter region = EMEA).

## 4. Style it so it reads like the repo charts

- Theme: light background `#fcfcfb`, text `#0b0b0b`, secondary text `#52514e`, gridlines `#e1e0d9`.
- Series colors in this order: `#2a78d6` (blue), `#eb6834` (orange), `#1baf7a` (aqua). Use gray `#c3c2b7` for the "before" or "default" series and blue for the one that matters.
- One color per single-series chart. Turn on data labels only for the value you're making a point about.
- Add a text box at the top of each page with the finding in one sentence, the same wording as the README.

## 5. Share it

Share > Manage access > "Anyone with the link can view", then add the link to this README under the overview image.
