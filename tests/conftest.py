import importlib
import warnings
from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base


warnings.filterwarnings(
    "ignore",
    message=r"datetime\.datetime\.utcnow\(\) is deprecated and scheduled for removal in a future version.*",
    category=DeprecationWarning,
)


def pytest_configure() -> None:
    warnings.filterwarnings(
        "ignore",
        message=r"datetime\.datetime\.utcnow\(\) is deprecated and scheduled for removal in a future version.*",
        category=DeprecationWarning,
    )


class FakeRedis:
    def __init__(self) -> None:
        self.storage: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.storage.get(key)

    async def setex(self, key: str, _: int, value: str) -> None:
        self.storage[key] = value

    async def delete(self, *keys: str) -> None:
        for key in keys:
            self.storage.pop(key, None)

    def reset(self) -> None:
        self.storage.clear()


class DummyScheduler:
    def add_job(self, *args, **kwargs) -> None:
        return None

    def start(self) -> None:
        return None

    def shutdown(self, wait: bool = False) -> None:
        return None


@pytest.fixture(scope="session")
def fake_redis() -> FakeRedis:
    return FakeRedis()


@pytest_asyncio.fixture(scope="session")
async def test_engine(tmp_path_factory: pytest.TempPathFactory):
    db_path = tmp_path_factory.mktemp("db") / "test.sqlite3"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", future=True)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest_asyncio.fixture(scope="session")
async def session_factory(test_engine):
    factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    return factory


@pytest_asyncio.fixture(autouse=True)
async def clean_state(session_factory, fake_redis: FakeRedis):
    async with session_factory() as session:
        for table in reversed(Base.metadata.sorted_tables):
            await session.execute(table.delete())
        await session.commit()
    fake_redis.reset()


@pytest.fixture(scope="session")
def app_module(session_factory, test_engine, fake_redis: FakeRedis):
    import app.core.redis_client as redis_client_module
    import app.db.session as db_session_module
    import app.services.cache_service as cache_service_module

    db_session_module.engine = test_engine
    db_session_module.AsyncSessionLocal = session_factory
    redis_client_module.redis_client = fake_redis
    cache_service_module.redis_client = fake_redis

    import app.main as main_module

    main_module = importlib.reload(main_module)
    main_module.scheduler = DummyScheduler()
    return main_module


@pytest_asyncio.fixture
async def client(app_module) -> AsyncIterator[httpx.AsyncClient]:
    app = app_module.app
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as async_client:
            yield async_client


@pytest_asyncio.fixture
async def db_session(session_factory):
    async with session_factory() as session:
        yield session
