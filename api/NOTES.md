# Alembic

Generate migration script: `uv run alembic revision --autogenerate -m "<description>"`

Upgrade to revision: `uv run alembic upgrade <version>|head`

# Rungoal CLI

Commands from `rungoal.cli` are available through `pyproject.toml` as `rungoal-cli.exe`

### Example: Grabbing all runs and associated data this year:

Get runs for user 1, since Jan 1, 2026, and put them in `tmp(/runs)`:

`uv run rungoal-cli fetch-runs 1 2026-01-01 --output tmp`

Get heart rate data for user 1, for the time periods specified by runs in `tmp/runs`, and put them in `tmp(/heartRates)`:

`uv run rungoal-cli fetch-heart-rates 1 --output tmp --from-runs-path tmp/runs`

Get TCX files for user 1, for the runs found in `tmp/runs`, and put them in `tmp(/tcx)`:

`uv run rungoal-cli fetch-tcx 1 --output tmp --from-runs-path tmp/runs`