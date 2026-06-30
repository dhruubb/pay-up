from sqlalchemy.ext.asyncio import (

AsyncSession,

async_sessionmaker,

create_async_engine,

)

from app.core.config import settings

DATABASE_URL = settings.DATABASE_URL.replace(

"postgresql+psycopg://",

"postgresql+psycopg_async://",

)

engine = create_async_engine(

DATABASE_URL,

echo=False,

future=True,

)

AsyncSessionLocal = async_sessionmaker(

bind=engine,

class_=AsyncSession,

expire_on_commit=False,

)

async def get_db():

    async with AsyncSessionLocal() as session:

        yield session
