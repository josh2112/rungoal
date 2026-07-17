## TODO

There's always a problem. Now the syncer never finishes, never sets is_synced to True; just stops responding.
Looks like there's a problem with the database after syncing is all finished... but with the
code in place for creating the DB at startup, no more log info gets printed out...

Also figure out how to put "/rungoal" path in .env

### Flow

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
