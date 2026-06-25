## Fitbit

Surprise, TCX file includes heart rate data, and the resolution is better than the huge heart rate JSON

Interesting stuff from run datapoint:
 - start/end time
 - calories, steps, dist, avg pace, elev. gain, active duration (this excludes pauses)
 - "mobility metrics" averages: cadence, stride length, vert. oscillation, etc.

Interesting stuff from TCX file:
 - Time (store as seconds elapsed since start)
 - lat/lon (is there a clever way to store this? like offset from previous lat/lon?)
 - alt
 - total dist
 - heart rate

Also include for each run:
 - data source (fitbit, runtracker)
 - historical weather data (temp, humidity, cloud cover) for each run
 - likely running location (Sherman Branch, Veteran's Park, etc.) computed from GPS track
   - Do we want to geolocate? Or have most common run places plugged in?

# RunTracker

Import from runsession contains: date, duration, distance, calories

Seems that fitbit also has these runs going back a long way (thanks to sync from samsung health?)
 - but not as far as runtracker (2021 vs Nov 2023)
 - also missing calories

First-time sync algorithm:
 1) All the fitbit data
 2) Do we have a runtracker.db user with matching email? If so:
   - try to match each run (by date) to an existing run
     - match? take ONLY CALORIES (fitbit already has dist & duration, and the real start/end time) and ADD THEM to existing calories (in case we have 2 runs on the same day)
     - else, import