## Installation

Serve the backend with `unicorn`, `gunicorn` or similar, then have your web server direct all traffic under a certain path to the server proxy.

In production, the backend serves the frontend via `FastAPI.frontend()`. When a request comes in that can't be matched to one of the API paths, it is redirected to `/ui/dist/index.html`, where Vite takes over.

In development, the frontend actually serves the backend. Spin up the frontend with `npm run dev` and the backend with `uv run fastapi dev`, then point your web browser at the address Vite gives you. It directs any requests rooted at `/api` to the backend.

## Database

Regular old SQLite3, managed with Alembic. It lives at `/data/rungoal.db`.

Generate migration script: `uv run alembic revision --autogenerate -m "<description>"`

Upgrade to revision: `uv run alembic upgrade <version>|head`
