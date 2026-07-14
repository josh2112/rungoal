## TODO

- Use bootstrap multiple progress bars example (https://getbootstrap.com/docs/5.3/components/progress/#multiple-bars) to show sync progress
- Make a "delete last run" CLI command so we can debug syncing
- We're missing a 5-mile run on July 8! Figure out why...
    - Something weird is happening with syncing. Starting from July 6, the July 8 run is synced, but then it is deleted when the July 13 run is synced?
    - The lower bound of the Google Health sync is the start_time of the latest run... but somehow THAT run doesn't get returned in the results, so we delete it!
    - Is this a difference between start_time and exercise.interval.civil_start_time?

### Flow

After login and /user/me:

- Check sync state, and start streaming sync events if in progress
- If not is onboarded, Account.vue will handle onboarding
- Else:
    - Get initial set of runs (past 4 weeks)
    - If no sync is in progress, start one.

Every time sync is done:

- if we have runs: ask for any runs matching returned sync span
- if not, just get past 4 weeks

* No auto-sync in dev mode!

Features:

- Figure out likely running location (Sherman Branch, Veteran's Park, etc.) computed from GPS track
    - Geohash 7 chars
    - Refer to Gemini chat about how to download local park data boundaries and convert to geohash set
    - Precompute set of geohashed trackpoints for run
    - Find the park with the most overlap between park geohashes and run trackpoint geohashes
- Heatmap: Make a histogram grid of run trackpoint geohashes. Probably a library for this.
- Calendar view: Simple calendar month view with run days circled. Tapping a day takes you to the runs for that day.
- Heart rate stats:
    - Custom calculation of zones based on highest heart rate ever recorded
    - % of time in each zone

## TODO later

Use GH users/me/settings endpoint to get user-preferred distance and temperature units
