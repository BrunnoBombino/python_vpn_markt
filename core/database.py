import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

# Имя файла базы данных SQLite
DB_FILE = "users.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DB_FILE}"

# Создаем асинхронный движок для работы с БД
engine = create_async_engine(DATABASE_URL, echo=False)

# Создаем фабрику асинхронных сессий (через них будем делать запросы)
async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Базовый класс, от которого будут наследоваться все наши таблицы
class Base(DeclarativeBase):
    pass


async def init_db():
    """Служебная функция для автоматического создания таблиц при старте системы"""
    async with engine.begin() as conn:
        # Импортируем модели внутри функции, чтобы избежать циклического импорта
        from core.models import User
        await conn.run_sync(Base.metadata.create_all)
    print("🗄️ База данных и таблицы успешно инициализированы.")
