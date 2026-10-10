# Football Analytics Project

Sharon's own football data analytics project — portfolio piece and testbed for
answering concrete football questions (e.g. "is Barcelona's hot start
statistically real?", "how should Barcelona press PSG?") using proper
data science methodology.

Built from scratch, structured after and reusing analysis code from
[jakeyk11/football-data-analytics](https://github.com/jakeyk11/football-data-analytics)
(Apache-2.0 licensed — see `LICENSE`). Credit to Jake Kolliari (@_JKDS_) for the
original tools and model code.

## Structure

```
football_project/
├── analysis_tools/        # Reused data-engineering / modelling helper modules
├── data_directory/         # Raw and processed data, by source
│   └── understat_data/      # Match + player data pulled from understat.com
│       └── PULL_PROCEDURE.md  # How to pull more (repeatable, browser-driven)
├── model_directory/        # Pretrained models (xG, pass clustering)
├── projects/                # One folder per question/analysis, numbered
└── notebooks/                # Exploratory work
```

## Data access — important findings (2026-10-10)

This environment's sandboxed shell can only reach GitHub and package
registries directly. Scraping football data sources from Python
(`requests`, `understatapi`, `ScraperFC`, etc.) does **not** work here out of
the box:

- **fbref.com** — reachable, but puts up an actual Cloudflare CAPTCHA
  (checkbox challenge) that cannot and should not be automated around.
  `ScraperFC`'s own `FBref` scraper depends on `botasaurus`, a stealth
  browser package, for exactly this reason — and `botasaurus` doesn't
  install cleanly in this sandbox either (build failures on its
  `pytweening` dependency).
- **understat.com** — blocked by this environment's shell-level network
  allowlist when called via `requests`/`understatapi` directly (proxy
  returns 403). It **does** load fine through the linked browser (the
  `mcp__remote-devices__Claude_Browser__*` tools), with no CAPTCHA.

**Working approach:** understat.com exposes a clean JSON endpoint
(`getTeamData/<team>/<year>`) that the team pages themselves call. It can't
be hit directly, but its response is readable off the browser's network log
right after the team page loads. The full repeatable procedure is in
`data_directory/understat_data/PULL_PROCEDURE.md`. Saved match data loads
into a clean DataFrame via `analysis_tools/understat_data_engineering.py`
(`load_team_matches()`, `season_summary()`).

`data_directory/understat_data/barcelona_2026_matches.json` and
`psg_2026_matches.json` are the first real pulls this way — confirmed:
Barcelona really are 7 wins from 7 with 31 goals scored (xG 29.4, so the
output roughly matches underlying chance quality, not just hot finishing),
PSG are 2W–2D–1L from 5.

**Revisit later:** if a proper scraping setup is wanted (e.g. running this
outside the sandbox, or with a paid data API), `ScraperFC`'s FBref/Understat
clients and the original repo's Whoscored/Opta pipeline become usable
directly — the blocker is this specific environment, not the approach.

## Pretrained models carried over

- `model_directory/xg_model/log_regression_xg_model.joblib` — logistic
  regression expected-goals model, trained on 40,000+ shots across Europe's
  big five leagues, 2017/18 season.
- `model_directory/pass_cluster_model/PassClusterModel65.joblib` — k-means
  model assigning passes to one of 65 clusters, trained on 5M+ passes,
  2019/20–2022/23.

Both are historical training snapshots, not live/current-season models —
treat predictions accordingly, and prefer retraining on fresher data for
anything where recency matters.

**Caveat confirmed by testing:** the xG model was pickled with scikit-learn
1.2.1; this environment has 1.9.1. It loads and runs, but scikit-learn
prints an `InconsistentVersionWarning` and warns results could be affected —
worth a quick validation (re-score a few known shots, sanity-check the
output) before trusting it for anything that matters, rather than assuming
it transferred cleanly.

## Setup

```
pip install -r requirements.txt
```

See `requirements.txt` for what's confirmed working vs. optional.
