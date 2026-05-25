import asyncio
import logging
import uvicorn
from fastapi import FastAPI

# Импортируем готовые объекты из модулей инициализации
from bot.init_bot import bot, dp
from core.init_api import api
from core.database import init_db
from core.auth import WEB_HOST, WEB_PORT

# Импортируем СБОРЩИКИ роутеров из файлов __init__.py
from bot.handlers import router as bot_router
from web.routes import api_router


# Настройка логгера
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Инициализируем веб-сервер
app = FastAPI(title="VPN Management System")

# Подключаем роутеры
dp.include_router(bot_router)
app.include_router(api_router)


async def run_bot():
    """Запуск Telegram-бота"""
    logger.info("🤖 Запуск Telegram-бота...")

    # Автоматически лечим базу данных и проверяем аварийный бэкап 3x-ui перед стартом
    try:
        await init_db()
        api.restore_lost_users()
    except Exception as e:
        logger.error(f"⚠️ Ошибка при инициализации сервисов: {e}")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


async def run_web():
    """Запуск веб-сервера FastAPI"""
    logger.info(f"💻 Запуск Веб-интерфейса на http://{WEB_HOST}:{WEB_PORT}...")
    config = uvicorn.Config(app=app, host=WEB_HOST, port=WEB_PORT, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    """Главная точка входа"""
    await asyncio.gather(
        run_bot(),
        run_web()
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("🛑 Система полностью остановлена.")
