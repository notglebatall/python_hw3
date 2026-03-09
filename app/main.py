from contextlib import asynccontextmanager
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.auth_router import router as auth_router
from app.api.links_router import router as links_router
from app.api.public_router import router as public_router
from app.core.settings import settings
from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine
import app.models.link  # noqa: F401
import app.models.user  # noqa: F401
from app.tasks.cleanup import cleanup_expired_and_unused_links


scheduler = AsyncIOScheduler()


async def run_cleanup_job() -> None:
    async with AsyncSessionLocal() as session:
        await cleanup_expired_and_unused_links(session)


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    scheduler.add_job(run_cleanup_job, "interval", minutes=1, id="cleanup_links", replace_existing=True)
    scheduler.start()
    yield
    scheduler.shutdown(wait=False)


WEB_DIR = Path(__file__).resolve().parent / "web"

app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")

app.include_router(auth_router)
app.include_router(links_router)


@app.get("/")
async def index_page():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/health")
async def healthcheck():
    return {"status": "ok"}


app.include_router(public_router)
