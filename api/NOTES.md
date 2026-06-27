## TODO

Importing TCX takes a long time. Most of them are empty. Can we avoid downloading/processing TCX when we know we have no GPS data? Can we rely on Run.exercise.exerciseMetadata.hasGps to know whether there's a TCX or not? Gemini says yes but double-check: Verify there are no TCX files with valid trackpoints for which the corresponding run has hasGPS = False or missing.
71 tcx with track data
69 run with hasGPS

Some of the trackpoint data looks sus. For example, not every run has a datapoint in the first second. Check:

- Timestamp of first datapoint for each run
- Timestamp of last datapoint for each run (is it close to run.end_time - run.start_time?)
- Distance of last datapoint for each run (is it close to run.distance_millimeters?)

## Fitbit

Also include for each run:

- historical weather data (temp, humidity, cloud cover) for each run
- likely running location (Sherman Branch, Veteran's Park, etc.) computed from GPS track
    - Do we want to geolocate? Or have most common run places plugged in?

# RunTracker

Import from runsession contains: date, duration, distance, calories

Seems that fitbit also has these runs going back a long way (thanks to sync from samsung health?)

- but not as far as runtracker (2021 vs Nov 2023)
- also missing calories

First-time sync algorithm:

1.  All the fitbit data
2.  Do we have a runtracker.db user with matching email? If so:

- try to match each run (by date) to an existing run
    - match? take ONLY CALORIES (fitbit already has dist & duration, and the real start/end time) and ADD THEM to existing calories (in case we have 2 runs on the same day)
    - else, import
