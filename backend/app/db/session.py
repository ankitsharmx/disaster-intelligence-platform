from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.ext.compiler import compiles
from geoalchemy2 import Geometry
from geoalchemy2.admin import select_dialect
import geoalchemy2.admin.dialects.sqlite as sqlite_admin
from app.core.config import settings

# Graceful SQLite compatibility: compile Geometry as BLOB and disable spatialite extensions on SQLite
@compiles(Geometry, "sqlite")
def compile_geometry_sqlite(type_, compiler, **kw):
    return "BLOB"


sqlite_admin.before_create = lambda *args, **kwargs: None
sqlite_admin.after_create = lambda *args, **kwargs: None
sqlite_admin.before_drop = lambda *args, **kwargs: None
sqlite_admin.after_drop = lambda *args, **kwargs: None

Geometry.bind_expression = lambda self, bindvalue: bindvalue
Geometry.column_expression = lambda self, col: col
Geometry.result_processor = lambda self, dialect, coltype: (lambda value: value)

# Engine setup
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
