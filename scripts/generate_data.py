"""Generates a realistic, fully synthetic CRM dataset for a fictional B2B SaaS company.

Every number comes from a seeded simulation, so the dataset is reproducible
and contains no real company or personal data. A few business "stories" are
built in for the analysis to find (see README):

  * Partner-sourced deals win more often; outbound wins less often.
  * Mid-Market deals stall in the Proposal stage.
  * One EMEA Mid-Market AE carries lots of pipeline but converts poorly.
  * An EMEA SDR left at the end of June 2026 and wasn't replaced, so EMEA
    outbound pipeline (and future coverage) drops.

Usage: python scripts/generate_data.py   (writes data/*.csv)
"""
from __future__ import annotations

import itertools
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
START = date(2025, 1, 1)
SNAPSHOT = datetime(2026, 10, 27, 18, 0)  # "today" for the dataset
OUT = Path(__file__).resolve().parent.parent / "data"

rng = np.random.default_rng(SEED)

REGIONS = ["AMER", "EMEA", "APAC"]
SEGMENTS = ["SMB", "Mid-Market", "Enterprise"]
SOURCES = ["Inbound", "Outbound", "Partner", "Events"]
STAGES = ["Discovery", "Demo", "Proposal", "Negotiation"]

# ---------------------------------------------------------------- people
AES = [  # (owner_id, name, segment, region, start, skill, proposal_drag)
    ("AE01", "Avery Brooks", "Enterprise", "AMER", "2024-03-01", 1.02, 1.0),
    ("AE02", "Camille Laurent", "Enterprise", "EMEA", "2023-09-01", 1.00, 1.0),
    ("AE03", "Mei Tanaka", "Enterprise", "APAC", "2024-01-15", 0.98, 1.0),
    ("AE04", "Sam Rivera", "Mid-Market", "AMER", "2023-06-01", 1.03, 1.0),
    ("AE05", "Taylor Brooks", "Mid-Market", "AMER", "2025-07-01", 0.97, 1.0),
    ("AE06", "Ines Moreau", "Mid-Market", "EMEA", "2024-02-01", 1.08, 0.9),
    ("AE07", "Oliver Grant", "Mid-Market", "EMEA", "2024-05-01", 0.86, 1.6),
    ("AE08", "Arjun Rao", "Mid-Market", "APAC", "2024-04-01", 1.00, 1.0),
    ("AE09", "Casey Nguyen", "SMB", "AMER", "2024-08-01", 1.04, 1.0),
    ("AE10", "Noemie Petit", "SMB", "EMEA", "2024-10-01", 1.00, 1.0),
]
# APAC SMB deals are covered by the APAC Mid-Market AE.
POD = {(seg, reg): [a[0] for a in AES if a[2] == seg and a[3] == reg] for seg in SEGMENTS for reg in REGIONS}
POD[("SMB", "APAC")] = ["AE08"]

SDRS = [  # (owner_id, name, region, start, end)
    ("SD01", "Riley Chen", "AMER", "2024-01-01", None),
    ("SD02", "Morgan Hayes", "AMER", "2024-06-01", None),
    ("SD03", "Lea Dubois", "EMEA", "2024-03-01", None),
    ("SD04", "Ben Fischer", "EMEA", "2024-03-01", "2026-06-30"),  # left, not replaced
    ("SD05", "Priya Shah", "APAC", "2024-09-01", None),
]

AE_INFO = {a[0]: a for a in AES}
# Chance that a deal which has really died is left open in the CRM instead of being closed out.
ZOMBIE_RATE = {"AE01": 0.12, "AE07": 0.25}
DEFAULT_ZOMBIE_RATE = 0.06


def d(s: str | None) -> date | None:
    return date.fromisoformat(s) if s else None


def active(start: str, end: str | None, day: date) -> bool:
    return d(start) <= day and (end is None or day <= d(end))


# ---------------------------------------------------------------- funnel parameters
INBOUND_BASE = {"AMER": 110, "EMEA": 70, "APAC": 25}
PARTNER_BASE = {"AMER": 12, "EMEA": 10, "APAC": 4}
EVENT_PEAK = {"AMER": 60, "EMEA": 45, "APAC": 15}
EVENT_LOW = {"AMER": 8, "EMEA": 6, "APAC": 2}
EVENT_MONTHS = {3, 6, 10}
OUTBOUND_PER_SDR = 30
MONTHLY_GROWTH = 1.025
SEASON = {8: 0.75, 12: 0.7}

SEGMENT_MIX = {
    "Inbound": [0.55, 0.33, 0.12],
    "Outbound": [0.25, 0.45, 0.30],
    "Partner": [0.20, 0.45, 0.35],
    "Events": [0.35, 0.40, 0.25],
}
MQL_RATE = {"Inbound": 0.50, "Outbound": 0.22, "Partner": 0.65, "Events": 0.30}
SQL_RATE = {"SMB": 0.55, "Mid-Market": 0.50, "Enterprise": 0.45}
OPP_RATE = 0.82

ADVANCE = {  # chance of moving to the next stage (last one = chance to win)
    "SMB": [0.72, 0.70, 0.72, 0.80],
    "Mid-Market": [0.68, 0.64, 0.60, 0.75],
    "Enterprise": [0.62, 0.60, 0.58, 0.70],
}
SOURCE_LIFT = {"Inbound": 1.03, "Outbound": 0.92, "Partner": 1.10, "Events": 0.98}
DAYS_IN_STAGE = {  # mean days spent in each stage
    "SMB": [6, 9, 8, 6],
    "Mid-Market": [9, 13, 22, 12],
    "Enterprise": [16, 22, 30, 24],
}
DEAL_SIZE = {"SMB": (9_000, 0.45), "Mid-Market": (32_000, 0.50), "Enterprise": (110_000, 0.55)}
LOST_REASONS = {
    "Discovery": (["No need", "No budget", "Timing", "Unresponsive"], [0.35, 0.25, 0.20, 0.20]),
    "Demo": (["Product gap", "Timing", "Competitor", "Unresponsive"], [0.30, 0.25, 0.20, 0.25]),
    "Proposal": (["Price", "Competitor", "No decision", "Timing"], [0.35, 0.30, 0.25, 0.10]),
    "Negotiation": (["Price", "Competitor", "No decision", "Legal / procurement"], [0.40, 0.25, 0.25, 0.10]),
}
INDUSTRIES = ["Software", "Logistics", "Healthcare", "Manufacturing", "Financial Services", "Retail"]
EMPLOYEES = {"SMB": ["11-50", "51-200"], "Mid-Market": ["201-500", "501-1,000"], "Enterprise": ["1,001-5,000", "5,000+"]}
COUNTRIES = {"AMER": ["United States", "Canada", "Brazil", "Mexico"], "EMEA": ["United Kingdom", "Germany", "France", "Netherlands", "Spain", "Sweden"],
             "APAC": ["Australia", "Singapore", "Japan", "India"]}
COUNTRY_P = {"AMER": [0.70, 0.15, 0.10, 0.05], "EMEA": [0.30, 0.25, 0.20, 0.10, 0.08, 0.07], "APAC": [0.40, 0.25, 0.20, 0.15]}

SYL = ["vel", "mor", "an", "tri", "lux", "cor", "ven", "ar", "bel", "kin", "sol", "nor", "pax", "quin", "ral",
       "tor", "zen", "ly", "dra", "ost", "mer", "fen", "gal", "hal", "rion", "tes", "vant", "il", "ove", "ux"]
NOUN = {"Software": ["Software", "Labs", "Cloud", "Systems"], "Logistics": ["Freight", "Logistics", "Shipping"],
        "Healthcare": ["Health", "Care", "Medical"], "Manufacturing": ["Industries", "Manufacturing", "Works"],
        "Financial Services": ["Capital", "Finance", "Payments"], "Retail": ["Retail", "Goods", "Stores"]}


def company_name(industry: str, used: set[str]) -> str:
    while True:
        n = rng.integers(2, 4)
        stem = "".join(rng.choice(SYL, n)).capitalize()
        name = f"{stem} {rng.choice(NOUN[industry])}"
        if name not in used:
            used.add(name)
            return name


def month_starts():
    m = START
    while m <= SNAPSHOT.date():
        yield m
        m = (m.replace(day=28) + timedelta(days=4)).replace(day=1)


def rand_day_in_month(m: date) -> datetime:
    nxt = (m.replace(day=28) + timedelta(days=4)).replace(day=1)
    last = min(nxt - timedelta(days=1), SNAPSHOT.date())
    day = m + timedelta(days=int(rng.integers(0, (last - m).days + 1)))
    return datetime.combine(day, datetime.min.time()) + timedelta(hours=int(rng.integers(8, 19)), minutes=int(rng.integers(0, 60)))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    used_names: set[str] = set()
    accounts, leads, opps, history = [], [], [], []
    acct_by_key: dict[tuple, list[str]] = {}
    rr_ae = {k: itertools.cycle(v) for k, v in POD.items()}
    sdr_cycle: dict[str, int] = {r: 0 for r in REGIONS}

    for mi, m in enumerate(month_starts()):
        growth = MONTHLY_GROWTH ** mi
        season = SEASON.get(m.month, 1.0)
        for region in REGIONS:
            sdrs_now = [s for s in SDRS if s[2] == region and active(s[3], s[4], m)]
            volumes = {
                "Inbound": INBOUND_BASE[region] * growth * season,
                "Outbound": OUTBOUND_PER_SDR * len(sdrs_now) * season,
                "Partner": PARTNER_BASE[region] * growth,
                "Events": (EVENT_PEAK if m.month in EVENT_MONTHS else EVENT_LOW)[region] * growth,
            }
            if m.year == SNAPSHOT.year and m.month == SNAPSHOT.month:  # partial month
                frac = SNAPSHOT.day / 31
                volumes = {k: v * frac for k, v in volumes.items()}
            for source, vol in volumes.items():
                for _ in range(rng.poisson(vol)):
                    created = rand_day_in_month(m)
                    if created > SNAPSHOT:
                        continue
                    segment = rng.choice(SEGMENTS, p=SEGMENT_MIX[source])
                    # Account: sometimes a second lead from a company we already know.
                    key = (segment, region)
                    if acct_by_key.get(key) and rng.random() < 0.15:
                        account_id = rng.choice(acct_by_key[key])
                    else:
                        industry = rng.choice(INDUSTRIES)
                        account_id = f"A{len(accounts) + 1:05d}"
                        accounts.append({
                            "account_id": account_id, "account_name": company_name(industry, used_names),
                            "industry": industry, "segment": segment,
                            "employee_band": rng.choice(EMPLOYEES[segment]), "region": region,
                            "country": rng.choice(COUNTRIES[region], p=COUNTRY_P[region]),
                        })
                        acct_by_key.setdefault(key, []).append(account_id)

                    sdr = None
                    if sdrs_now:
                        sdr = sdrs_now[sdr_cycle[region] % len(sdrs_now)][0]
                        sdr_cycle[region] += 1
                    lead = {"lead_id": f"L{len(leads) + 1:06d}", "account_id": account_id, "created_at": created,
                            "source": source, "segment": segment, "region": region, "sdr_owner_id": sdr,
                            "mql_at": None, "sql_at": None, "opportunity_id": None}
                    leads.append(lead)

                    if rng.random() >= MQL_RATE[source]:
                        continue
                    lead["mql_at"] = created + timedelta(hours=float(rng.uniform(1, 72)))
                    if lead["mql_at"] > SNAPSHOT:
                        lead["mql_at"] = None
                        continue
                    if rng.random() >= SQL_RATE[segment]:
                        continue
                    lead["sql_at"] = lead["mql_at"] + timedelta(days=float(rng.uniform(1, 7)))
                    if lead["sql_at"] > SNAPSHOT:
                        lead["sql_at"] = None
                        continue
                    if rng.random() >= OPP_RATE:
                        continue
                    opp_created = lead["sql_at"] + timedelta(days=float(rng.uniform(0, 5)))
                    if opp_created > SNAPSHOT:
                        continue
                    # Assign the AE: round robin inside the pod, skipping people who hadn't started yet.
                    for _ in range(5):
                        ae = next(rr_ae[key])
                        if d(AE_INFO[ae][4]) <= opp_created.date():
                            break
                    opp_id = f"O{len(opps) + 1:05d}"
                    lead["opportunity_id"] = opp_id
                    opps.append(simulate_opportunity(opp_id, lead, ae, opp_created, history))

    write(accounts, leads, opps, history)


def simulate_opportunity(opp_id, lead, ae, created, history):
    seg, source = lead["segment"], lead["source"]
    _, _, _, _, _, skill, drag = AE_INFO[ae]
    median, sigma = DEAL_SIZE[seg]
    amount = float(np.round(rng.lognormal(np.log(median), sigma) * (1.1 if source == "Partner" else 1.0), -2))

    t = created
    state = {"stage": "Discovery", "is_closed": False, "is_won": False, "lost_reason": None, "closed_at": None}
    for i, stage in enumerate(STAGES):
        mean_days = DAYS_IN_STAGE[seg][i] * (drag if stage == "Proposal" else 1.0)
        p = min(0.95, ADVANCE[seg][i] * SOURCE_LIFT[source] * skill)
        advances = rng.random() < p
        stay = float(rng.gamma(2.0, mean_days / 2.0)) * (1.0 if advances else 1.2)
        exit_t = t + timedelta(days=max(0.5, stay))
        if exit_t > SNAPSHOT:  # still sitting in this stage today
            history.append({"opportunity_id": opp_id, "stage": stage, "entered_at": t, "exited_at": None})
            state["stage"] = stage
            break
        history.append({"opportunity_id": opp_id, "stage": stage, "entered_at": t, "exited_at": exit_t})
        t = exit_t
        if not advances and rng.random() < ZOMBIE_RATE.get(ae, DEFAULT_ZOMBIE_RATE):
            # The deal went quiet but nobody closed it: it sits in this stage indefinitely.
            history[-1]["exited_at"] = None
            state["stage"] = stage
            break
        if not advances:
            reasons, probs = LOST_REASONS[stage]
            state.update(stage="Closed Lost", is_closed=True, lost_reason=str(rng.choice(reasons, p=probs)), closed_at=t)
            history.append({"opportunity_id": opp_id, "stage": "Closed Lost", "entered_at": t, "exited_at": None})
            break
        if i == len(STAGES) - 1:
            state.update(stage="Closed Won", is_closed=True, is_won=True, closed_at=t)
            history.append({"opportunity_id": opp_id, "stage": "Closed Won", "entered_at": t, "exited_at": None})

    pushes = 0
    if state["is_closed"]:
        close_date = state["closed_at"].date()
        forecast_category = "Closed"
    else:
        # Reps set an expected close date; when it passes, most push it out, some forget.
        typical = sum(DAYS_IN_STAGE[seg]) * float(rng.uniform(0.8, 1.3))
        close_date = (created + timedelta(days=typical)).date()
        # Reps push a passed close date a few times, then often stop updating it.
        while close_date < SNAPSHOT.date() and pushes < 4 and rng.random() < 0.7:
            close_date = close_date + timedelta(days=int(rng.integers(14, 45)))
            pushes += 1
        forecast_category = {"Discovery": "Pipeline", "Demo": "Pipeline", "Proposal": "Best Case",
                             "Negotiation": "Commit"}[state["stage"]]
    last_change = max(h["entered_at"] for h in history if h["opportunity_id"] == opp_id)
    return {
        "opportunity_id": opp_id, "account_id": lead["account_id"], "lead_id": lead["lead_id"], "owner_id": ae,
        "created_at": created, "stage": state["stage"], "amount": amount, "close_date": close_date,
        "is_closed": state["is_closed"], "is_won": state["is_won"], "lost_reason": state["lost_reason"],
        "forecast_category": forecast_category, "source": source, "segment": seg, "region": lead["region"],
        "last_stage_change_at": last_change, "close_date_pushes": pushes,
    }


# Quarterly quota at 2025-Q1, set per AE from the size of their territory.
# Calibrated so a typical AE lands near 95% in expectation (checked over 24 random seeds);
# AEs in the same pod share a quota, so differences in attainment come from performance.
QUOTA_BASE = {"AE01": 430_000, "AE02": 260_000, "AE03": 110_000, "AE04": 180_000, "AE05": 180_000,
              "AE06": 170_000, "AE07": 170_000, "AE08": 150_000, "AE09": 230_000, "AE10": 130_000}


def quotas() -> pd.DataFrame:
    """Quarterly new-business ACV quota per AE, with a 50% ramp in an AE's first quarter."""
    rows = []
    for ae in AES:
        for q in pd.period_range("2025Q1", "2027Q1", freq="Q"):
            q_start = q.start_time.date()
            q_end = q.end_time.date()
            start = d(ae[4])
            if start > q_end:
                continue
            ramp = 0.5 if start >= q_start else 1.0  # an AE's first quarter is a ramp quarter
            uplift = 1.0 + 0.03 * (q.ordinal - pd.Period("2025Q1", freq="Q").ordinal)  # quota grows 3% a quarter
            rows.append({"owner_id": ae[0], "quarter": str(q), "quarter_start": q_start,
                         "quota": round(QUOTA_BASE[ae[0]] * ramp * uplift, -3)})
    return pd.DataFrame(rows)


def write(accounts, leads, opps, history) -> None:
    owners = [{"owner_id": a[0], "owner_name": a[1], "role": "AE", "segment": a[2], "region": a[3],
               "start_date": a[4], "end_date": None} for a in AES]
    owners += [{"owner_id": s[0], "owner_name": s[1], "role": "SDR", "segment": None, "region": s[2],
                "start_date": s[3], "end_date": s[4]} for s in SDRS]
    frames = {
        "owners": pd.DataFrame(owners),
        "quotas": quotas(),
        "accounts": pd.DataFrame(accounts),
        "leads": pd.DataFrame(leads),
        "opportunities": pd.DataFrame(opps),
        "opportunity_stage_history": pd.DataFrame(history),
    }
    frames["opportunities"]["amount"] = frames["opportunities"]["amount"].astype(int)
    for name, df in frames.items():
        for col in df.columns:
            if col.endswith("_at"):  # timestamps to whole seconds; missing stays empty
                df[col] = pd.to_datetime(df[col]).dt.strftime("%Y-%m-%d %H:%M:%S")
        df.to_csv(OUT / f"{name}.csv", index=False)
        print(f"{name:28s} {len(df):>6,} rows")


if __name__ == "__main__":
    main()
