# import json
#
# from core.init_api import api
#
# with open("users.json", "w", encoding="utf-8") as file:
#     json.dump(api.users(), file, indent=4, ensure_ascii=False)

import asyncio
from datetime import datetime, timedelta, timezone
from core.database import async_session, init_db
from core.models import User


async def create_test_profile():
    # 1. На всякий случай инициализируем базу данных, если файла еще нет
    await init_db()

    # НАСТРОЙКА ТЕСТОВЫХ ДАННЫХ ДЛЯ ВАШЕЙ МОДЕЛИ
    test_username = "test"  # Логин для поиска в админке
    test_email = "test_mail@example.com"  # Почта для сайта
    test_tg_id = 999999999  # Вымышленный Telegram ID

    # Ставим дату окончания подписки, например, вчерашнюю (чтобы проверить начисление дней с нуля)
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    # Убираем таймзону для совместимости с вашей колонкой DateTime в SQLite
    expiry_date_naive = yesterday.replace(tzinfo=None)

    async with async_session() as session:
        # Проверяем, нет ли уже такого пользователя в базе
        from sqlalchemy import select

        query = select(User).where(User.username == test_username)
        result = await session.execute(query)
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print(
                f"⚠️ Пользователь с username '{test_username}' уже существует в БД!"
            )
            return

        # 2. Создаем объект пользователя строго по вашей структуре модели
        test_user = User(
            telegram_id=test_tg_id,
            username=test_username,
            email=test_email,
            password_hash=None,  # Пароль для теста можно оставить пустым
            vpn_uuid=None,  # UUID пока нет, так как в панели 3x-ui его еще не создавали
            vpn_sub_id=None,  # subId тоже пустой
            vpn_inbound_remark="Limit",  # Помещаем в стандартный лимитный инбаунд
            expiry_date=expiry_date_naive,
        )

        session.add(test_user)
        await session.commit()

        print("\n" + "=" * 45)
        print(f"✅ ТЕСТОВЫЙ ПОЛЬЗОВАТЕЛЬ УСПЕШНО СОЗДАН!")
        print(f"👤 Username (логин): {test_username}")
        print(f"🆔 Telegram ID: {test_tg_id}")
        print(f"📧 Email сайта: {test_email}")
        print(f"📍 Тариф в БД: limit")
        print(f"📅 Срок подписки: Истек вчера (готов к продлению)")
        print("=" * 45 + "\n")


if __name__ == "__main__":
    # Запускаем асинхронную функцию создания
    asyncio.run(create_test_profile())
