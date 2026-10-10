# How to pull understat.com team data (repeatable procedure)

This environment cannot call understat.com directly from Python (`requests`,
`understatapi`) — the sandbox's network allowlist blocks it at the proxy
level (403). It works fine through the linked browser. This is the
step-by-step for pulling a team's season data cleanly.

## Steps

1. **Navigate the browser to the team's page:**
   `https://understat.com/team/<Team_Name>/<season_start_year>`
   e.g. `https://understat.com/team/Barcelona/2026`, or
   `https://understat.com/team/Paris_Saint_Germain/2026` (underscores for
   multi-word names in the URL path).

   `<season_start_year>` is the year the season *started* in (so the
   2026/27 season is `2026`).

2. **Read the network request log** for that tab and find the
   `getTeamData/<team>/<year>` request — this fires automatically when the
   page loads. It returns clean JSON: `dates` (every match, past and
   upcoming, with goals/xG/result/win-draw-loss forecast probabilities) and
   `players` (season-aggregate player stats: goals, xG, xA, shots, key
   passes, xGChain, xGBuildup).

   Do **not** try to `fetch()` this endpoint manually from the browser's
   JS console — it 404s outside of the page's own load sequence (some
   request-specific check, not yet figured out why). Reading it off the
   already-fired network request is the reliable method.

3. **Save the match data** into
   `data_directory/understat_data/<team>_<year>_matches.json`, re-shaped
   per match as `{id, side, home, away, goals, xG, datetime, forecast,
   result}` — see the existing `barcelona_2026_matches.json` /
   `psg_2026_matches.json` for the exact shape. Only keep `isResult: true`
   entries for completed matches; note the next upcoming fixture separately
   if useful.

   If the player array is needed too, save it as
   `<team>_<year>_players.json` the same way (watch out: on at least one
   pull, PSG's player list from this endpoint included several names that
   don't match PSG's actual squad — worth a sanity check against a second
   source before trusting individual player numbers from here).

4. **Load it in Python** with
   `analysis_tools/understat_data_engineering.py` —
   `load_team_matches(filepath)` returns a clean one-row-per-match
   DataFrame from that team's own perspective (not home/away-keyed), and
   `season_summary(df)` gives a quick sanity-check aggregate.

## Why not just script this end-to-end?

Because step 1–2 need a real browser driven turn-by-turn (navigate, then
read the network log) — there's no way to do it as an unattended Python
script in this sandbox. Each new team/season pull is a short manual-ish
pass through steps 1–3, done once per team per session, not a cron job.
If this project ever runs outside this sandbox (a normal machine with open
internet), the `ScraperFC.Understat` client wraps the same endpoint
properly and this whole procedure becomes a one-line call instead.

## fbref.com — not currently usable

fbref.com shows an actual Cloudflare CAPTCHA checkbox when loaded through
the browser. That's not something to automate past — if fbref data is
needed later, that requires either a different access method entirely
(a paid API, a different environment) or doing the lookup manually outside
this session.
