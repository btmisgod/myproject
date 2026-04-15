from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import install_exception_handlers
from app.core.logging import configure_logging
from app.db.bootstrap import bootstrap_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    await bootstrap_database()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

install_exception_handlers(app)
app.include_router(api_router, prefix="/api/v1")
app.mount("/community/assets", StaticFiles(directory="app/web"), name="community-assets")


@app.get("/", include_in_schema=False)
async def community_index() -> FileResponse:
    return FileResponse("app/web/index.html")


@app.get("/community", include_in_schema=False)
async def community_root() -> FileResponse:
    return FileResponse("app/web/index.html")
