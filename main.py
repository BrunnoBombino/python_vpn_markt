from core.API import API
from core.database import init_db


api = API


async def run_bot():
    """Запуск Telegram-бота в режиме Long Polling"""
    logger.info("🤖 Запуск Telegram-бота...")

    # Сначала автоматически инициализируем базу данных на диске
    try:
        await init_db()  # <-- ДОБАВЛЕНО СЮДА
    except Exception as e:
        logger.error(f"Не удалось инициализировать базу данных: {e}")

    # Затем запускаем наш менеджер 3x-ui
    try:
        api.restore_lost_users()
    except Exception as e:
        logger.error(f"Не удалось запустить экстренное восстановление: {e}")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)
