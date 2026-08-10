- Turns out the only required subelement of a TCX <Trackpoint> is time?? Position, altitude, distance and heart rate are all optional, and it looks like the first 3 of those are not recorded while paused. This will majorly effect efficiency calculations. We need all 3 of distance, altitude and heart rate to compute a efficiency.
    - First, we need to separate pauses from data hiccups. If we have 5 or 10 seconds of missing data but the trackpoints on either side of them have that data, we can extrapolate (note: 5 or 10 is a guess, we need to see how big the gaps typically are; refer to the .TCX files from runs for 8/7 and 8/10). If multiple trackpoints with only time, that's a pause.
    - Remove trackpoints associated with a pause but put a marker there; we don't want stat splits extending over a pause.
    - Next, extrapolate individual data. For each metric:
        - Look for a missing value.
        - Find the non-missing values on either side of it.
        - If the data gap is longer than 5-10 seconds (see note above), treat it as a pause; remove this section from consideration and put a marker so we don't put a split over it.
        - Otherwise, extrapolate the missing values from the endpoints.
    - Generate splits as continuous trackpoint lists of around 5 minutes, respecting the markers. If we end up with any
      tiny splits, join them to the previous split.
    - Calculate metrics as usual.
    - Observations from analyze_stats:
        - HR gaps are never more than 1 or 2 trackpoints wide, can comfortably interpolate
        - distance and altitude gaps always go together, and ara varying sizes from 1 to 160 or more

- Make average run efficiency (meters per heartbeat) a first-class metric on the run card
- Heatmap: Make a histogram grid of run trackpoint geohashes. Probably a library for this.
- Calendar view: Simple calendar month view with run days circled. Tapping a day takes you to the runs for that day.
- Use GH users/me/settings endpoint to get user-preferred distance and temperature units
