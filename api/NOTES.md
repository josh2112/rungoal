## TODO

Add an endpoint which returns 'interesting' runs:
 - Longest run
 - Hottest/coldest runs (by apparent temperature)
 - earliest/latest run
 - Most efficient run
 - Wettest run

- Figure out likely running location (Sherman Branch, Veteran's Park, etc.) computed from GPS track
    - Geohash 7 chars
    - Refer to Gemini chat about how to download local park data boundaries and convert to geohash set
    - Precompute set of geohashed trackpoints for run
    - Find the park with the most overlap between park geohashes and run trackpoint geohashes

- Heatmap: Make a histogram grid of run trackpoint geohashes. Probably a library for this.

- Calendar view: Simple calendar month view with run days circled. Tapping a day takes you to the runs for that day.

## TODO later

Use GH users/me/settings endpoint to get user-preferred distance and temperature units
