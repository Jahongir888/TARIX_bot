from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from database.models import Base

# SQLite asinxron fayl manzili
DATABASE_URL = "sqlite+aiosqlite:///./database.db"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)

# Jadvallarni avtomatik yaratish funksiyasi
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)