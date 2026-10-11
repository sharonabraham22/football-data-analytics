"""
barcelona_hot_start_analysis.py

Question: Barcelona opened 2026/27 with 8 wins from 8 and 34 goals scored
(29.4 -> 32.32 xG as more matches came in). Is that a real signal of an
elite team, or well within normal variance for a strong side that just
got some bounces?

Method (same core assumption the original jakeyk11 repo's expected-points
model uses, see model_directory/ and analysis_tools/models.py):
treat each match's goals as Poisson-distributed around that match's own
xG. This is standard in football analytics - xG is literally built to
approximate "expected number of goals from these chances" - and lets us
ask: given the ACTUAL quality of chances Barcelona created and conceded
in each of these 8 games, how often would a randomly-reshuffled version
of the same underlying performances still produce an unbeaten,
30+-goal start?

This isolates "were the underlying performances actually this dominant"
from "did they get unusually lucky with finishing" - the two explanations
that get conflated when people see a scoreline like this.
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from analysis_tools.understat_data_engineering import load_team_matches, season_summary

RNG_SEED = 42
N_SIMULATIONS = 50_000

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(HERE, "..", "..", "data_directory", "understat_data", "barcelona_2026_matches.json")


def run_monte_carlo(matches_df, n_sims=N_SIMULATIONS, seed=RNG_SEED):
    """
    For each match, draw simulated goals_for ~ Poisson(xg_for) and
    goals_against ~ Poisson(xg_against), independently, n_sims times.
    This answers: "given the chances actually created/conceded in these
    specific 8 games, how variable is the resulting record?"

    Returns a DataFrame of per-simulation outcomes: wins, draws, losses,
    total goals scored, whether the simulation matched or exceeded the
    real result (8 wins, 30+ goals).
    """
    rng = np.random.default_rng(seed)
    n_matches = len(matches_df)
    xg_for = matches_df["xg_for"].to_numpy()
    xg_against = matches_df["xg_against"].to_numpy()

    # shape: (n_sims, n_matches)
    sim_goals_for = rng.poisson(lam=xg_for, size=(n_sims, n_matches))
    sim_goals_against = rng.poisson(lam=xg_against, size=(n_sims, n_matches))

    sim_wins = (sim_goals_for > sim_goals_against).sum(axis=1)
    sim_draws = (sim_goals_for == sim_goals_against).sum(axis=1)
    sim_losses = (sim_goals_for < sim_goals_against).sum(axis=1)
    sim_total_goals = sim_goals_for.sum(axis=1)

    return pd.DataFrame({
        "wins": sim_wins,
        "draws": sim_draws,
        "losses": sim_losses,
        "total_goals": sim_total_goals,
    })


def summarize(sims, actual_wins, actual_goals, n_matches):
    n_sims = len(sims)
    p_unbeaten = (sims["losses"] == 0).mean()
    p_perfect_record = (sims["wins"] == n_matches).mean()
    p_30_plus_goals = (sims["total_goals"] >= 30).mean()
    p_both = ((sims["wins"] == n_matches) & (sims["total_goals"] >= 30)).mean()

    print(f"\nMonte Carlo: {n_sims:,} simulated {n_matches}-match stretches,")
    print("each match's goals drawn as Poisson(that match's own xG).\n")

    print(f"Actual record:        {actual_wins}-0-0, {actual_goals} goals")
    print(f"Mean simulated wins:   {sims['wins'].mean():.2f} / {n_matches}")
    print(f"Mean simulated goals:  {sims['total_goals'].mean():.2f}\n")

    print(f"P(unbeaten, i.e. 0 losses across all {n_matches}):      {p_unbeaten:.1%}")
    print(f"P(perfect record, {n_matches} wins from {n_matches}):           {p_perfect_record:.1%}")
    print(f"P(30+ goals across the {n_matches} matches):          {p_30_plus_goals:.1%}")
    print(f"P(perfect record AND 30+ goals):          {p_both:.1%}")

    win_dist = sims["wins"].value_counts(normalize=True).sort_index()
    print(f"\nFull distribution of simulated win counts (out of {n_matches}):")
    for w, p in win_dist.items():
        bar = "#" * int(p * 100)
        print(f"  {w} wins: {p:6.1%}  {bar}")

    return {
        "p_unbeaten": p_unbeaten,
        "p_perfect_record": p_perfect_record,
        "p_30_plus_goals": p_30_plus_goals,
        "p_both": p_both,
        "win_dist": win_dist,
    }


def per_match_finishing_check(matches_df):
    """
    Separate sanity check: does actual goals-for track xG-for closely on a
    per-match basis? If Barcelona were just getting lucky bounces, we'd
    expect goals >> xG consistently. If the run is "real" (chance quality
    actually was that high), goals and xG should track each other.
    """
    df = matches_df.copy()
    df["over_performance"] = df["goals_for"] - df["xg_for"]
    print("\nPer-match goals vs xG (finishing over/under-performance):")
    print(df[["date", "opponent", "goals_for", "xg_for", "over_performance"]]
          .assign(date=lambda d: d["date"].dt.strftime("%Y-%m-%d"))
          .to_string(index=False))
    corr = df["goals_for"].corr(df["xg_for"])
    print(f"\nCorrelation(goals_for, xg_for) across these {len(df)} matches: {corr:.2f}")
    return df


def plot_win_distribution(sims, actual_wins, n_matches, out_path):
    """
    Bar chart of the simulated win-count distribution, with the bar for
    Barcelona's actual result (8 wins) highlighted in a distinct color.
    Single hue for the distribution (magnitude), one accent for the
    highlighted/actual value - no legend needed since the highlighted bar
    is directly labeled.
    """
    BLUE = "#2a78d6"
    ORANGE = "#eb6834"
    TEXT_PRIMARY = "#0b0b0b"
    TEXT_SECONDARY = "#52514e"

    counts = sims["wins"].value_counts(normalize=True).reindex(range(n_matches + 1), fill_value=0)

    fig, ax = plt.subplots(figsize=(8, 5), dpi=150)
    colors = [ORANGE if w == actual_wins else BLUE for w in counts.index]
    bars = ax.bar(counts.index, counts.values * 100, color=colors, width=0.65, zorder=3)

    for w, pct in zip(counts.index, counts.values * 100):
        if pct > 0.5:
            ax.text(w, pct + 0.8, f"{pct:.0f}%", ha="center", va="bottom",
                     fontsize=9, color=TEXT_SECONDARY)

    actual_pct = counts.loc[actual_wins] * 100
    ax.annotate(
        f"Actual result: {actual_wins}-0-0\n({actual_pct:.0f}% of simulations)",
        xy=(actual_wins, actual_pct), xytext=(actual_wins - 2.3, actual_pct + 10),
        fontsize=10, color=TEXT_PRIMARY, fontweight="bold",
        arrowprops=dict(arrowstyle="->", color=TEXT_PRIMARY, lw=1.2),
    )

    ax.set_xlabel("Wins out of 8 matches", fontsize=10, color=TEXT_SECONDARY)
    ax.set_ylabel("Share of simulated 8-match stretches", fontsize=10, color=TEXT_SECONDARY)
    ax.set_title(
        "Simulating Barcelona's 8-game start 50,000 times\n"
        "(each match's goals drawn from that match's own actual xG)",
        fontsize=12, color=TEXT_PRIMARY, loc="left", pad=14,
    )
    ax.set_xticks(range(n_matches + 1))
    ax.yaxis.set_major_formatter(lambda x, _: f"{x:.0f}%")
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#d8d7d0")
    ax.tick_params(colors=TEXT_SECONDARY, labelsize=9)
    ax.grid(axis="y", color="#eceae3", zorder=0)
    ax.set_axisbelow(True)

    fig.tight_layout()
    fig.savefig(out_path, facecolor="white")
    plt.close(fig)
    print(f"\nSaved chart to {out_path}")


if __name__ == "__main__":
    matches = load_team_matches(DATA_PATH)
    summary = season_summary(matches)
    print("=== Barcelona 2026/27 season to date ===")
    print(summary)

    per_match_finishing_check(matches)

    sims = run_monte_carlo(matches)
    results = summarize(sims, actual_wins=summary["wins"], actual_goals=summary["goals_for"], n_matches=summary["played"])

    chart_path = os.path.join(HERE, "win_distribution.png")
    plot_win_distribution(sims, actual_wins=summary["wins"], n_matches=summary["played"], out_path=chart_path)
