## TODO

Think about flow how does sync and downloading runs (locally) work?
 1 Sync, then ask for all runs?
 2 Ask for all runs, then sync, and sync returns any new runs at the end?

Not 2. It would be more responsive (we have some runs right away), but sync should not return runs.
How about this:
 1) Get baseline (runs for past 2 weeks maybe)
 2) Sync
 3) When sync is complete, ask for any runs matching sync parameters (by default, date since last run)
 That way sync works with different time periods. Say you edited a month-old run in Fitbit. You could then have the
 backend sync the time period around that run, then ask for the runs in that time period.
 Leads to this: sync should have same parameters as fetch: a 'from' and optional 'to'.

Paging:
  Start with 2 weeks of run data (plus whatever we sync). When hit bottom, ask for previous 2 weeks.

Onboarding:
 - After getting user info (/user/me), do onboarding if !is_onboarded
   - Little dialog asking if user wants to sync runtracker

Features:
 - Figure out likely running location (Sherman Branch, Veteran's Park, etc.) computed from GPS track
    - Geohash 7 chars
    - Refer to Gemini chat about how to download local park data boundaries and convert to geohash set
    - Precompute set of geohashed trackpoints for run
    - Find the park with the most overlap between park geohashes and run trackpoint geohashes
 - Heatmap: Make a histogram grid of run trackpoint geohashes. Probably a library for this.
 - Calendar view: Simple calendar month view with run days circled. Tapping a day takes you to the runs for that day.

# TODO later

Use GH users/me/settings endpoint to get user-preferred distance and temperature units
