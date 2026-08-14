Heatmap: Follow this example: https://github.com/LumenResearch/heatmappy/blob/master/heatmappy/heatmap.py (don't want to pull this library in because it depends on matplotlib and a bunch of other stuff)

- Pregenerate a nice fuzzy grayscale point image (farther from center = less white) and a nice gradient to map to
- For the tile, create a n 'F' mode image (32-bit floating point), all black, and paste the point image onto it for each lat/lon
- Map the grayscale image to color using the gradient
- Apply a little opacity

- Calendar view: Simple calendar month view with run days circled. Tapping a day takes you to the runs for that day.
