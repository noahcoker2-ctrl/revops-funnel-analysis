"""Recomputes the headline metrics with pandas, independently of the SQL, and
checks they match the SQL results in results/. Run after run_analysis.py.

Usage: python scripts/verify_metrics.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA, RES = ROOT / "data", ROOT / "results"
AS_OF = pd.Timestamp("2026-10-27")

opps = pd.read_csv(DATA / "opportunities.csv", parse_dates=["created_at", "close_date", "last_stage_change_at"])
leads = pd.read_csv(DATA / "leads.csv", parse_dates=["created_at", "mql_at", "sql_at"])
hist = pd.read_csv(DATA / "opportunity_stage_history.csv", parse_dates=["entered_at", "exited_at"])
owners = pd.read_csv(DATA / "owners.csv")
quotas = pd.read_csv(DATA / "quotas.csv")

checks: list[tuple[str, float, float]] = []


def check(name: str, ours: float, sql: float) -> None:
    checks.append((name, float(ours), float(sql)))


# 1. Win rate and lead-to-MQL by source
sql = pd.read_csv(RES / "02_funnel_by_source.csv").set_index("source")
merged = leads.merge(opps[["opportunity_id", "is_closed", "is_won"]], on="opportunity_id", how="left")
for src, g in merged.groupby("source"):
    closed = g[g.is_closed == True]  # noqa: E712 (NaN for leads without an opportunity)
    check(f"win rate, {src}", round(closed.is_won.mean(), 3), sql.loc[src, "win_rate"])
    check(f"lead to MQL, {src}", round(g.mql_at.notna().mean(), 3), sql.loc[src, "lead_to_mql"])

# 2. Stage advance rate and median days, by segment
sql = pd.read_csv(RES / "03_stage_conversion.csv").set_index(["segment", "stage"])
h = hist.sort_values(["opportunity_id", "entered_at"]).copy()
h["next_stage"] = h.groupby("opportunity_id").stage.shift(-1)
h = h.merge(opps[["opportunity_id", "segment"]], on="opportunity_id")
h = h[h.stage.isin(["Discovery", "Demo", "Proposal", "Negotiation"]) & h.exited_at.notna()]
for (seg, stage), g in h.groupby(["segment", "stage"]):
    check(f"advance rate, {seg} {stage}", round((g.next_stage != "Closed Lost").mean(), 3), sql.loc[(seg, stage), "advance_rate"])
    days = (g.exited_at - g.entered_at).dt.total_seconds() // 60 / 1440
    check(f"median days, {seg} {stage}", round(days.median(), 1), sql.loc[(seg, stage), "median_days_in_stage"])

# 3. Sales velocity by segment
sql = pd.read_csv(RES / "05_sales_velocity.csv").set_index("segment")
win = opps[opps.is_closed & opps.close_date.between("2025-10-01", "2026-09-30")]
made = opps[opps.created_at.dt.normalize().between("2025-10-01", "2026-09-30")]
for seg in ["SMB", "Mid-Market", "Enterprise"]:
    w = win[win.segment == seg]
    won = w[w.is_won]
    n = (made.segment == seg).sum() / 4
    cycle = (won.close_date - won.created_at.dt.normalize()).dt.days.mean()
    v = n * w.is_won.mean() * won.amount.mean() / cycle
    check(f"velocity per day, {seg}", round(v), sql.loc[seg, "velocity_per_day"])

# 4. Pipeline coverage, reported and clean, for 2026-Q4
sql = pd.read_csv(RES / "06_pipeline_coverage.csv")
sql = sql[sql.quarter == "2026-Q4"].set_index("region")
q4 = opps.close_date.between("2026-10-01", "2026-12-31")
at_risk = (opps.close_date < AS_OF) | (opps.last_stage_change_at < AS_OF - pd.Timedelta(days=30)) | (opps.close_date_pushes >= 2)
qa = quotas[quotas.quarter == "2026Q4"].merge(owners, on="owner_id").groupby("region").quota.sum()
for region in ["AMER", "EMEA", "APAC"]:
    in_r = opps.region == region
    won = opps[q4 & in_r & opps.is_won].amount.sum()
    remaining = qa[region] - won
    pipe = opps[q4 & in_r & ~opps.is_closed]
    check(f"coverage, {region}", round(pipe.amount.sum() / remaining, 2), sql.loc[region, "coverage"])
    clean = pipe[~at_risk[pipe.index]].amount.sum()
    check(f"clean coverage, {region}", round(clean / remaining, 2), sql.loc[region, "clean_coverage"])

# 5. Historical chance of winning from each stage (deals closed in the last 365 days)
sql = pd.read_csv(RES / "07b_stage_win_probability.csv").set_index(["segment", "stage"])
recent = opps[opps.is_closed & (opps.close_date >= AS_OF - pd.Timedelta(days=365))]
reached = hist.merge(recent[["opportunity_id", "segment", "is_won"]], on="opportunity_id")
reached = reached[reached.stage.isin(["Discovery", "Demo", "Proposal", "Negotiation"])].drop_duplicates(["opportunity_id", "stage"])
for (seg, stage), g in reached.groupby(["segment", "stage"]):
    check(f"historical p(win), {seg} {stage}", round(g.is_won.mean(), 3), sql.loc[(seg, stage), "historical_p_win"])

# 6. AE attainment over the last four full quarters
sql = pd.read_csv(RES / "08_rep_scorecard.csv").set_index("ae")
win4 = opps[opps.is_won & opps.close_date.between("2025-10-01", "2026-09-30")].groupby("owner_id").amount.sum()
q4s = quotas[quotas.quarter.isin(["2025Q4", "2026Q1", "2026Q2", "2026Q3"])].groupby("owner_id").quota.sum()
for _, ae in owners[owners.role == "AE"].iterrows():
    check(f"attainment, {ae.owner_name}", round(win4.get(ae.owner_id, 0) / q4s[ae.owner_id], 3), sql.loc[ae.owner_name, "attainment"])

# 7. Won ACV per lead and average won deal by source
sql = pd.read_csv(RES / "02_funnel_by_source.csv").set_index("source")
for src, g in merged.merge(opps[["opportunity_id", "amount"]], on="opportunity_id", how="left").groupby("source"):
    won = g[g.is_won == True]  # noqa: E712
    check(f"won ACV per lead, {src}", round(won.amount.sum() / len(g)), sql.loc[src, "won_acv_per_lead"])
    check(f"avg won ACV, {src}", round(won.amount.mean()), sql.loc[src, "avg_won_acv"])

# 8. Outbound pipeline created per month by region (2026)
sql = pd.read_csv(RES / "11_outbound_trend.csv", parse_dates=["month"]).set_index(["region", "month"])
ob = opps[(opps.source == "Outbound") & (opps.created_at >= "2026-01-01")].copy()
ob["month"] = ob.created_at.dt.to_period("M").dt.to_timestamp()
ob_sum = ob.groupby(["region", "month"]).amount.sum()
for (region, month), row in sql.iterrows():
    check(f"outbound pipeline, {region} {month:%Y-%m}", ob_sum.get((region, month), 0.0), row.outbound_pipeline)

# 9. Q4 2026 forecast attainment, fixed-default and historical probabilities
sql = pd.read_csv(RES / "07_forecast.csv").set_index("region")
default_p = {"Discovery": 0.10, "Demo": 0.25, "Proposal": 0.50, "Negotiation": 0.75}
hist_p = reached.groupby(["segment", "stage"]).is_won.mean()
open_q4 = opps[q4 & ~opps.is_closed]
for region in ["AMER", "EMEA", "APAC"]:
    o = open_q4[open_q4.region == region]
    won = opps[q4 & opps.is_won & (opps.region == region)].amount.sum()
    crm = (o.amount * o.stage.map(default_p)).sum()
    hist_w = (o.amount * [hist_p[(sg, st)] for sg, st in zip(o.segment, o.stage)]).sum()
    check(f"forecast attainment (fixed default), {region}", round((won + crm) / qa[region], 3), sql.loc[region, "attainment_fixed_default"])
    check(f"forecast attainment (historical), {region}", round((won + hist_w) / qa[region], 3), sql.loc[region, "attainment_historical"])

# 10. AE win rate, days in Proposal (last four quarters), open deals and at-risk share
score = pd.read_csv(RES / "08_rep_scorecard.csv").set_index("ae")
hyg = pd.read_csv(RES / "09_pipeline_hygiene.csv").set_index("ae")
closed4 = opps[opps.is_closed & opps.close_date.between("2025-10-01", "2026-09-30")]
prop = hist[(hist.stage == "Proposal") & hist.exited_at.dt.normalize().between("2025-10-01", "2026-09-30")]
prop = prop.merge(opps[["opportunity_id", "owner_id"]], on="opportunity_id")
prop_days = ((prop.exited_at - prop.entered_at).dt.total_seconds() // 60 / 1440).groupby(prop.owner_id).median()
open_now = opps[~opps.is_closed]
for _, ae in owners[owners.role == "AE"].iterrows():
    c = closed4[closed4.owner_id == ae.owner_id]
    check(f"win rate, {ae.owner_name}", round(c.is_won.mean(), 3), score.loc[ae.owner_name, "win_rate"])
    check(f"days in Proposal, {ae.owner_name}", round(prop_days[ae.owner_id], 1), score.loc[ae.owner_name, "median_days_in_proposal"])
    mine = open_now[open_now.owner_id == ae.owner_id]
    check(f"open deals, {ae.owner_name}", len(mine), hyg.loc[ae.owner_name, "open_deals"])
    risky = mine[at_risk[mine.index]]
    check(f"at-risk share, {ae.owner_name}", round(risky.amount.sum() / mine.amount.sum(), 3), hyg.loc[ae.owner_name, "at_risk_share"])

# 11. Lost reasons: share of each stage's losses
sql = pd.read_csv(RES / "10_lost_reasons.csv").set_index(["lost_at_stage", "lost_reason"])
lost = opps[opps.stage == "Closed Lost"][["opportunity_id", "lost_reason"]]
last_stage = (hist[hist.stage.isin(["Discovery", "Demo", "Proposal", "Negotiation"])]
              .sort_values("entered_at").groupby("opportunity_id").stage.last())
lost = lost.assign(lost_at_stage=lost.opportunity_id.map(last_stage))
shares = lost.groupby("lost_at_stage").lost_reason.value_counts(normalize=True)
for (stage, reason), row in sql.iterrows():
    check(f"loss share, {stage} / {reason}", round(shares[(stage, reason)], 3), row.share_of_stage_losses)

# Report
bad = [(n, a, b) for n, a, b in checks if not np.isclose(a, b, atol=1e-9, rtol=1e-9)]
print(f"{len(checks) - len(bad)}/{len(checks)} metrics match between pandas and SQL")
for n, a, b in bad:
    print(f"  MISMATCH {n}: pandas={a} sql={b}")
raise SystemExit(1 if bad else 0)
