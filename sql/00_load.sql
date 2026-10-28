-- Load the CSVs into DuckDB tables and define shared helpers.
-- Every other query runs against these tables, so they port easily to BigQuery or Postgres.
CREATE OR REPLACE TABLE owners AS SELECT * FROM read_csv_auto('data/owners.csv');
CREATE OR REPLACE TABLE quotas AS SELECT * FROM read_csv_auto('data/quotas.csv');
CREATE OR REPLACE TABLE accounts AS SELECT * FROM read_csv_auto('data/accounts.csv');
CREATE OR REPLACE TABLE leads AS SELECT * FROM read_csv_auto('data/leads.csv', timestampformat = '%Y-%m-%d %H:%M:%S');
CREATE OR REPLACE TABLE opportunities AS SELECT * FROM read_csv_auto('data/opportunities.csv', timestampformat = '%Y-%m-%d %H:%M:%S');
CREATE OR REPLACE TABLE opportunity_stage_history AS SELECT * FROM read_csv_auto('data/opportunity_stage_history.csv', timestampformat = '%Y-%m-%d %H:%M:%S');

-- The dataset's "today". Change this if you regenerate the data with a new snapshot.
CREATE OR REPLACE MACRO as_of() AS DATE '2026-10-27';
-- 2026-10-27 -> '2026-Q4'
CREATE OR REPLACE MACRO qlabel(ts) AS strftime(ts, '%Y') || '-Q' || quarter(ts);
CREATE OR REPLACE MACRO stage_order(s) AS CASE s WHEN 'Discovery' THEN 1 WHEN 'Demo' THEN 2 WHEN 'Proposal' THEN 3 WHEN 'Negotiation' THEN 4 END;
CREATE OR REPLACE MACRO segment_order(s) AS CASE s WHEN 'SMB' THEN 1 WHEN 'Mid-Market' THEN 2 WHEN 'Enterprise' THEN 3 END;
