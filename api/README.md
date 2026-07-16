This is a website to track your run data. It's probably not what you're looking for, as I coded it for me and my specific needs.

It's very much a work in progress.

## Planned capabilities

- Login with Google
- Sync run data from multiple sources:
    - Google Health (formerly Fitbit)
    - RunTracker (my previous run-tracking app)
- Show you all kinds of interesting data such as
    - Location of a run (computed from .TCX data)
    - Heart rate trends
    - A friendly name computed from the run data (such as "Afternoon Zone 2 run" or "Morning sprint")
- Goal tracking:
    - Set up one or more goals with a time period and target distance
    - See current goal status (completion percentage, how far behind or ahead you are)
    - See progress over time
- Heart rate zone computation based on maximum heart rate seen

# Coding details

AI was occasionally consulted for specific questions, but not a single line of code was copied and pasted. As Walter
White said, "I did this for me. I liked it, and I was good at it."

Frontend is Vite/Vue/Pinia/Axios/Bootstrap.

Backend is Python/FastAPI/SQLModel/Alembic.

## Rungoal CLI

The backend includes a little command-line app to allow experimenting with data retrieval and manipulation without
having to have the server runing. Commands from `rungoal/cli.py` are available as `rungoal-cli.exe`

### Example: Grabbing all runs and associated data this year:

Get runs for user 1, since Jan 1, 2026, and put them in `tmp(/runs)`:

`uv run rungoal-cli fetch-runs 1 2026-01-01 tmp`

Get TCX files for user 1, for the runs found in `tmp/runs`, and put them in `tmp(/tcx)`:

`uv run rungoal-cli fetch-tcx 1 --output tmp tmp/runs`

## Alembic

Generate migration script: `uv run alembic revision --autogenerate -m "<description>"`

Upgrade to revision: `uv run alembic upgrade <version>|head`
