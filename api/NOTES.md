Surprise, TCX file includes heart rate data, and the resolution is better than the huge heart rate JSON

Interesting stuff from run datapoint:
 - start/end time
 - calories, steps, dist, avg pace, elev. gain
 - "mobility metrics" averages: cadence, stride length, vert. oscillation, etc.

Interesting stuff from TCX file:
 - Time (store as seconds elapsed since start)
 - lat/lon (is there a clever way to store this? like offset from previous lat/lon?)
 - alt
 - total dist
 - heart rate

Also include for each run:
 - historical weather data (temp, humidity, cloud cover) for each run
 - likely running location (Sherman Branch, Veteran's Park, etc.) computed from GPS track
   - Do we want to geolocate? Or have most common run places plugged in?
