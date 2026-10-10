"""
understat_data_engineering.py

Loaders for data pulled from understat.com's getTeamData/<team>/<year> JSON
endpoint (see data_directory/understat_data/ and the "Data access" section
of the project README for how these files are obtained — this environment
can't call that endpoint directly from Python, so pulls go through the
browser and get saved here as JSON first).

Mirrors the role of whoscored_data_engineering.py / statsbomb_data_engineering.py
in the original jakeyk11/football-data-analytics repo: turn a raw saved
payload into clean, analysis-ready pandas DataFrames.
"""

import json
import pandas as pd


def load_team_matches(filepath):
    """
    Load a team's matches JSON (as saved from understat's getTeamData
    endpoint) into a clean, one-row-per-match DataFrame from that team's
    own perspective (goals_for/goals_against/xg_for/xg_against rather than
    home/away).

    Parameters
    ----------
    filepath : str
        Path to a *_matches.json file in data_directory/understat_data/

    Returns
    -------
    pd.DataFrame with columns:
        match_id, date, opponent, venue (H/A), goals_for, goals_against,
        xg_for, xg_against, result (W/D/L), win_prob, draw_prob, loss_prob
    """
    with open(filepath, "r") as f:
        payload = json.load(f)

    team_name = payload["team"]
    rows = []
    for m in payload["matches"]:
        is_home = m["side"] == "h"
        opponent = m["away"]["title"] if is_home else m["home"]["title"]
        goals_for = m["goals"]["h"] if is_home else m["goals"]["a"]
        goals_against = m["goals"]["a"] if is_home else m["goals"]["h"]
        xg_for = m["xG"]["h"] if is_home else m["xG"]["a"]
        xg_against = m["xG"]["a"] if is_home else m["xG"]["h"]

        # result is stored from the home team's perspective in the raw data;
        # re-derive from this team's own perspective instead of trusting it as-is
        if goals_for > goals_against:
            result = "W"
        elif goals_for < goals_against:
            result = "L"
        else:
            result = "D"

        rows.append({
            "match_id": m["id"],
            "date": m["datetime"],
            "team": team_name,
            "opponent": opponent,
            "venue": "H" if is_home else "A",
            "goals_for": goals_for,
            "goals_against": goals_against,
            "xg_for": xg_for,
            "xg_against": xg_against,
            "result": result,
            "win_prob": m["forecast"]["w"],
            "draw_prob": m["forecast"]["d"],
            "loss_prob": m["forecast"]["l"],
        })

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)


def season_summary(matches_df):
    """
    Quick aggregate summary of a team_matches DataFrame: record, goals,
    xG totals and per-game rates. Useful as a sanity check before running
    anything more involved (regression, Monte Carlo, etc).
    """
    n = len(matches_df)
    summary = {
        "played": n,
        "wins": (matches_df["result"] == "W").sum(),
        "draws": (matches_df["result"] == "D").sum(),
        "losses": (matches_df["result"] == "L").sum(),
        "goals_for": matches_df["goals_for"].sum(),
        "goals_against": matches_df["goals_against"].sum(),
        "xg_for": round(matches_df["xg_for"].sum(), 2),
        "xg_against": round(matches_df["xg_against"].sum(), 2),
        "goals_for_per_game": round(matches_df["goals_for"].mean(), 2),
        "xg_for_per_game": round(matches_df["xg_for"].mean(), 2),
        "goals_minus_xg": round(matches_df["goals_for"].sum() - matches_df["xg_for"].sum(), 2),
    }
    return summary


if __name__ == "__main__":
    import os
    here = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(here, "..", "data_directory", "understat_data")

    for fname, label in [
        ("barcelona_2026_matches.json", "Barcelona"),
        ("psg_2026_matches.json", "PSG"),
    ]:
        path = os.path.join(data_dir, fname)
        df = load_team_matches(path)
        print(f"\n=== {label} ===")
        print(df[["date", "opponent", "venue", "goals_for", "goals_against", "xg_for", "result"]])
        print(season_summary(df))
