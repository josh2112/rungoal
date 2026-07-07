## TODO

Flow:
After login and /user/me:
 - If not is_onboarded:
   - Little dialog asking if user wants to sync runtracker, then do a sync with that as a param
 - Otherwise:
   - Grab runs from past 2 weeks
   - Sync with no params
 
 Every time sync is done:
   - if we have runs: ask for any runs matching returned sync span
   - if not, just get past 2 weeks

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
