- Continuing trackpoint-filter saga: Latest run .TCX does in fact have heart rate gaps > 2 which I thought would never happen. Implemented a better filtering/interpolation solution for trackpoints, but it filters a bit too much. Doing the interpolation AFTER the grouping is not a great idea as we have to throw away endpoints that we could've otherwise interpreted had we had access to some valid data in the gaps. So:
  - First, break up the trackpoints where we have a big time gap (> 5 sec)
  - Next, interpolate on each group individually.
    - Don't trim end gaps, just skip over them.
  - Now, continue with the gap identification and splitting.
  
- Make average run efficiency (meters per heartbeat) a first-class metric on the run card
- Heatmap: Make a histogram grid of run trackpoint geohashes. Probably a library for this.
- Calendar view: Simple calendar month view with run days circled. Tapping a day takes you to the runs for that day.
- Use GH users/me/settings endpoint to get user-preferred distance and temperature units
