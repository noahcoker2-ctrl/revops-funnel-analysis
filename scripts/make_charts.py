"""Draws the README / LinkedIn charts from results/*.csv into charts/*.png.

Usage: python scripts/make_charts.py   (after run_analysis.py)
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RES, OUT = ROOT / "results", ROOT / "charts"

# Palette: validated categorical slots 1-3 plus neutral chrome (light mode).
SURFACE, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, NEUTRAL_FILL, SHADE = "#e1e0d9", "#c3c2b7", "#c3c2b7", "#f0efec"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "DejaVu Sans", "font.size": 10, "text.color": INK,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "axes.linewidth": 0.8,
    "xtick.color": MUTED, "ytick.color": INK2, "xtick.labelsize": 9, "ytick.labelsize": 9,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "grid.linestyle": "-",
    "axes.axisbelow": True, "legend.frameon": False, "legend.fontsize": 9,
    "text.parse_math": False,  # so "$" in labels prints as a dollar sign
})


def title(ax, text, sub=None):
    ax.set_title(text, loc="left", fontsize=12, fontweight="bold", color=INK, pad=22 if sub else 10)
    if sub:
        ax.text(0, 1.02, sub, transform=ax.transAxes, fontsize=9, color=INK2, va="bottom")


def coverage(ax):
    df = pd.read_csv(RES / "06_pipeline_coverage.csv")
    df = df[df.quarter == "2026-Q4"].set_index("region").loc[["AMER", "EMEA", "APAC"]]
    y = range(len(df))
    h = 0.36
    ax.barh([i + h / 2 for i in y], df.coverage, height=h, color=NEUTRAL_FILL, edgecolor=SURFACE, linewidth=2, label="Reported")
    ax.barh([i - h / 2 for i in y], df.clean_coverage, height=h, color=BLUE, edgecolor=SURFACE, linewidth=2, label="Clean: excludes stale,\npast-due and pushed deals")
    for i, (rep, cln) in enumerate(zip(df.coverage, df.clean_coverage)):
        ax.text(rep + 0.05, i + h / 2, f"{rep:.2f}x", va="center", fontsize=9, color=INK2)
        ax.text(cln + 0.05, i - h / 2, f"{cln:.2f}x", va="center", fontsize=9, color=INK, fontweight="bold")
    ax.axvline(3, color=MUTED, linewidth=1)
    ax.text(3.05, 0.97, "3x target", transform=ax.get_xaxis_transform(), fontsize=8, color=MUTED, ha="left", va="top")
    ax.set_yticks(list(y), df.index)
    ax.invert_yaxis()
    ax.set_xlim(0, 4.3)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Open pipeline closing this quarter / quota still to win")
    ax.legend(loc="center right", ncol=1, frameon=True, facecolor=SURFACE, edgecolor=SURFACE, framealpha=1)
    title(ax, "Q4 pipeline coverage by region", "Reported coverage hides how much of the pipeline is stale")


def win_by_source(ax):
    df = pd.read_csv(RES / "02_funnel_by_source.csv").sort_values("win_rate", ascending=True)
    ax.barh(df.source, df.win_rate, color=BLUE, height=0.55, edgecolor=SURFACE, linewidth=2)
    for i, (w, n) in enumerate(zip(df.win_rate, df.closed_opps)):
        ax.text(w + 0.006, i, f"{w:.0%}", va="center", fontsize=9, color=INK, fontweight="bold")
        ax.text(0.004, i - 0.38, f"{n} closed deals", va="center", fontsize=7.5, color=MUTED)
    ax.set_xlim(0, 0.4)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Win rate (won / closed opportunities)")
    best = df.iloc[-1]
    out = df.set_index("source").loc["Outbound", "win_rate"]
    title(ax, "Win rate by lead source", f"Outbound wins {out:.0%} of closed deals; {best.source} wins {best.win_rate:.0%}")


def days_in_stage(ax):
    df = pd.read_csv(RES / "03_stage_conversion.csv")
    stages = ["Discovery", "Demo", "Proposal", "Negotiation"]
    segs = [("SMB", BLUE), ("Mid-Market", ORANGE), ("Enterprise", AQUA)]
    w = 0.26
    for k, (seg, color) in enumerate(segs):
        vals = df[df.segment == seg].set_index("stage").loc[stages, "median_days_in_stage"]
        xs = [i + (k - 1) * w for i in range(len(stages))]
        ax.bar(xs, vals, width=w, color=color, edgecolor=SURFACE, linewidth=2, label=seg)
        if seg == "Mid-Market":
            v = vals["Proposal"]
            ax.annotate(f"{v:.0f} days", (xs[2], v), xytext=(0, 4), textcoords="offset points",
                        ha="center", fontsize=9, fontweight="bold", color=INK)
    ax.set_xticks(range(len(stages)), stages)
    ax.tick_params(axis="x", colors=INK2)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("Median days in stage")
    ax.legend(loc="upper left", ncol=3)
    ax.set_ylim(0, 32)
    mm = df[df.segment == "Mid-Market"].set_index("stage").median_days_in_stage
    title(ax, "Median days spent in each stage",
          f"Mid-Market deals spend {mm['Proposal']:.0f} days in Proposal, vs {mm['Demo']:.0f} in Demo and {mm['Negotiation']:.0f} in Negotiation")


def emea_outbound(ax):
    df = pd.read_csv(RES / "11_outbound_trend.csv", parse_dates=["month"])
    df = df[df.region == "EMEA"]
    labels = df.month.dt.strftime("%b")
    ax.axvspan(5.5, len(df) - 0.5, color=SHADE, zorder=0)
    ax.text(5.65, df.outbound_pipeline.max() / 1000 * 1.04, "One of two SDR seats empty", fontsize=8.5, color=INK2, va="bottom")
    ax.bar(range(len(df)), df.outbound_pipeline / 1000, color=BLUE, width=0.6, edgecolor=SURFACE, linewidth=2)
    h1 = df[df.month < "2026-07-01"].outbound_pipeline.mean() / 1000
    h2 = df[(df.month >= "2026-07-01") & (df.month < "2026-10-01")].outbound_pipeline.mean() / 1000
    ax.set_xticks(range(len(df)), labels)
    ax.tick_params(axis="x", colors=INK2)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("Outbound pipeline created ($k)")
    ax.set_ylim(0, df.outbound_pipeline.max() / 1000 * 1.18)
    title(ax, "EMEA outbound pipeline, 2026",
          f"Avg ${h1:,.0f}k/month Jan-Jun vs ${h2:,.0f}k Jul-Sep (October is month to date)")


def stage_probability(fig):
    df = pd.read_csv(RES / "07b_stage_win_probability.csv")
    stages = ["Discovery", "Demo", "Proposal", "Negotiation"]
    axes = fig.subplots(1, 3, sharey=True)
    for ax, seg in zip(axes, ["SMB", "Mid-Market", "Enterprise"]):
        d = df[df.segment == seg].set_index("stage").loc[stages]
        xs = range(len(stages))
        ax.bar([x - 0.19 for x in xs], d.fixed_default_p_win, width=0.36, color=NEUTRAL_FILL, edgecolor=SURFACE, linewidth=2, label="Fixed default (10/25/50/75%)")
        ax.bar([x + 0.19 for x in xs], d.historical_p_win, width=0.36, color=BLUE, edgecolor=SURFACE, linewidth=2, label="Historical (last 12 months)")
        ax.set_xticks(list(xs), ["Disc.", "Demo", "Prop.", "Neg."])
        ax.tick_params(axis="x", colors=INK2)
        ax.grid(axis="x", visible=False)
        ax.set_title(seg, loc="left", fontsize=10, color=INK, fontweight="bold")
        ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
        ax.set_ylim(0, 1)
    axes[0].set_ylabel("Chance a deal in this stage is won")
    axes[0].legend(loc="upper left")
    fig.suptitle("Fixed stage probabilities vs what actually happened", x=0.06, ha="left", fontsize=12, fontweight="bold", y=0.99)
    fig.text(0.06, 0.905, "Fixed defaults undervalue early SMB and Mid-Market deals and overvalue late Enterprise deals",
             fontsize=9, color=INK2)


def attainment(ax):
    df = pd.read_csv(RES / "08_rep_scorecard.csv").sort_values("attainment")
    ax.barh(df.ae, df.attainment, color=BLUE, height=0.6, edgecolor=SURFACE, linewidth=2)
    for i, (a, wr) in enumerate(zip(df.attainment, df.win_rate)):
        ax.text(a + 0.015, i, f"{a:.0%}  (win rate {wr:.0%})", va="center", fontsize=8.5, color=INK2,
                bbox=dict(facecolor=SURFACE, edgecolor="none", pad=1.5), zorder=3)
    ax.axvline(1, color=MUTED, linewidth=1)
    ax.set_xlim(0, 1.6)
    ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0, decimals=0))
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Quota attainment, 2025-Q4 to 2026-Q3")
    title(ax, "AE quota attainment, last four quarters")


def save(fig, name):
    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT / name, dpi=200, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    print("wrote", OUT / name)


def main():
    for fn, name, size in [(coverage, "coverage_q4.png", (7.5, 3.6)), (win_by_source, "win_rate_by_source.png", (7.5, 3.4)),
                           (days_in_stage, "days_in_stage.png", (7.5, 4)), (emea_outbound, "emea_outbound.png", (7.5, 3.8)),
                           (attainment, "rep_attainment.png", (7.5, 4.6))]:
        fig, ax = plt.subplots(figsize=size)
        fn(ax)
        save(fig, name)

    fig = plt.figure(figsize=(10, 4))
    stage_probability(fig)
    fig.subplots_adjust(top=0.78)
    save(fig, "stage_win_probability.png")

    # One overview image for posts.
    fig, axes = plt.subplots(2, 2, figsize=(15, 9.5))
    coverage(axes[0][0]); win_by_source(axes[0][1]); days_in_stage(axes[1][0]); emea_outbound(axes[1][1])
    fig.suptitle("RevOps funnel analysis: synthetic B2B SaaS CRM, Jan 2025 to Oct 2026", x=0.02, ha="left",
                 fontsize=15, fontweight="bold", y=1.0)
    fig.subplots_adjust(hspace=0.55, wspace=0.28, top=0.9)
    save(fig, "overview.png")


if __name__ == "__main__":
    main()
