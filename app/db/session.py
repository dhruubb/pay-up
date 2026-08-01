from sqlalchemy import event

from sqlalchemy.ext.asyncio import (

AsyncSession,

async_sessionmaker,

create_async_engine,

)

from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL.replace(

"sqlite://",

"sqlite+aiosqlite://",

)

engine = create_async_engine(

DATABASE_URL,

echo=False,

future=True,

)


@event.listens_for(engine.sync_engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

AsyncSessionLocal = async_sessionmaker(

bind=engine,

class_=AsyncSession,

expire_on_commit=False,

)

async def get_db():

    async with AsyncSessionLocal() as session:

        yield session
