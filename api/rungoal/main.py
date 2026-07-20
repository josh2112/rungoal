import tomllib

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from rungoal.cors import allowed_origins
from rungoal.errors import init_exception_handlers
from rungoal.routes import api
from rungoal.settings import settings

# ================ Init ================

with open("pyproject.toml", "rb") as f:
    metadata = tomllib.load(f)["project"]

app = FastAPI(
    root_path=settings.BASE_URL,
    title=metadata["name"],
    description=metadata["description"],
    version=metadata["version"],
    contact=metadata["authors"][0],
    redoc_url=None,
)

app.include_router(api)

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
