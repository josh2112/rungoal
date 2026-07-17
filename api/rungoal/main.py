from importlib.metadata import version

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from alembic import command
from alembic.config import Config
from rungoal.cors import allowed_origins
from rungoal.database import ensure_db_path_exists
from rungoal.errors import init_exception_handlers
from rungoal.routes import api
from rungoal.settings import settings

# ================ Init ================

# Create / upgrade the databse
alembic_config = Config("alembic.ini")
ensure_db_path_exists(alembic_config)
command.upgrade(alembic_config, "head")

app = FastAPI(
    title="RunGoal",
    version=version("rungoal"),
    docs_url="/api/docs",
    redoc_url=None,
)


app.include_router(api, prefix="/rungoal")

# Allow calls from the frontend on a different origin (not needed for production?)
if settings.DEV:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

init_exception_handlers(app)

# In production, FastAPI controls the flow. The web server will be set up to forward everything
# matching "/[baseUrl]/*" to us. FastAPI will process "/api" and anything else it has a route
# for, and serve the rest from the frontend's "dist" directory.
#
# For development, Vite controls the flow through a proxy in defineConfig() (see
# ../ui/vite.config.ts).

if not settings.DEV:
    app.frontend("/", directory="../ui/dist", fallback="index.html", check_dir=True)
