## TODO

Working on syncing directly from API bypassing disk.

Need to test new \_sync_runs() function.

1. Do a full sync with an empty database.
2. Do another sync with a fake set of 3 runs:
    - A brand-new run (should be added)
    - An existing run with modifications but same update_time (should be skipped)
    - An existing run with modifications but newer update_time (should be replaced)

- Download TCX files and return Trackpoint() instance lists
- Save to DB

## Fitbit

Also include for each run:

- historical weather data (temp, humidity, cloud cover) for each run
- likely running location (Sherman Branch, Veteran's Park, etc.) computed from GPS track
    - Do we want to geolocate? Or have most common run places plugged in?

# TODO later

Use GH users/me/settings endpoint to get user-preferred distance and temperature units
