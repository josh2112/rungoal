## TODO

We can now download run JSON and .TCX files to disk, then import them.
Next, do it all in one step. But GoogleClient functions need to return
records so we're not holding giant TCX files in memory.
Given a user ID and time period:

- Download runs and return Run() instannces
- Save to DB
- Download TCX files and return Trackpoint() instance lists
- Save to DB

## Fitbit

Also include for each run:

- historical weather data (temp, humidity, cloud cover) for each run
- likely running location (Sherman Branch, Veteran's Park, etc.) computed from GPS track
    - Do we want to geolocate? Or have most common run places plugged in?

# TODO later

Use GH users/me/settings endpoint to get user-preferred distance and temperature units
