from importlib.metadata import version

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from rungoal import auth
from rungoal.cors import allowed_origins
from rungoal.deps import DepSettings
from rungoal.errors import init_exception_handlers
from rungoal.routes import api

# ================ Init ================

app = FastAPI(title="RunGoal", version=version("rungoal"), docs_url="/api/docs", redoc_url=None)


app.include_router(api)

# Allow calls from the frontend on a different origin (not needed for production?)
if DepSettings().DEV:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

init_exception_handlers(app)
