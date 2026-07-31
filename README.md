# Rungoal

![Screenshot](/assets/Screenshot.png)

This website pulls data on your runs from Google Fit and tracks it against time and distance goals you specify. It's probably not what you're looking for, as I coded it for me and my specific needs.

## Planned capabilities

- Login with Google
- Sync run data from multiple sources:
    - Google Health (formerly Fitbit)
    - RunTracker (my previous run-tracking app)
- Show you all kinds of interesting data such as
    - Perceived "effort" per 5-minute split, computed as grade-adjusted distance divided by heart rate. Long distance/low heart rate = good (green), short distance/high heart rate = bad (red)
    - Location of a run (from OpenStreetMap data on nearby parks and trails)
    - Historical weather
- Goal tracking:
    - Set up one or more goals with a time period and target distance
    - See current goal status (completion percentage, how far behind or ahead you are)
    - See progress over time

# Coding details

AI was occasionally consulted for specific questions, but not a single line of code was copied and pasted. As Walter
White said, "I did this for me. I liked it, and I was good at it."

Frontend is Vite/Vue/Pinia/Axios/Bootstrap.

Backend is Python/FastAPI/SQLModel/Alembic.

## Rungoal CLI

The backend includes a little command-line app to allow experimenting with data retrieval and manipulation without
having to have the server runing. Commands from `rungoal/cli.py` are available as `rungoal-cli.exe`

### Example: Grabbing all recent runs and associated data:

Sync runs for user 1 since July 1, 2026. Any new runs are added any any existing runs whose updated date has changed are replaced. By default, this pulls down associated TCX data and the weather for the run, and attempts to determine the location of the run, pulling down additional parks and trails from OpenStreetMap if needed. It also calculates statistics for each 5-minute splits These features may be turned off with command-switches. GPS track, weather, location and split stats each also have their own sync commands.

`uv run rungoal-cli sync-runs 1 2026-07-01`
