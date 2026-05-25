import json
import secrets
import string
from pathlib import Path
from datetime import datetime, timedelta, timezone
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from core.auth import ADMIN_IDS
from sqlalchemy import func, select
from core.init_api import api
from core.database import async_session
from core.models import User
from bot.states import AdminPromoStates
from bot.keyboards.admin_kb import get_admin_main_keyboard


router = Router()

# Путь к файлу хранения промокодов (в корне проекта)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROMO_FILE = BASE_DIR / "promocodes.json"


def _load_promocodes() -> dict:
    """Вспомогательная функция чтения промокодов из JSON"""
    if not PROMO_FILE.exists() or PROMO_FILE.stat().st_size == 0:
        return {}
    try:
        with open(PROMO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_promocodes(data: dict):
    """Вспомогательная функция записи промокодов в JSON"""
    with open(PROMO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# ==========================================
#      БЛОК 1: ВХОД В АДМИНКУ
# ==========================================

# Вход в админку по команде /admin
@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return  # Игнорируем не-администраторов

    text = "⚙️ <b>Панель администратора VPN</b>\n\nВыберите необходимое действие:"
    await message.answer(text=text, reply_markup=get_admin_main_keyboard(), parse_mode="HTML")


# ==========================================
#      БЛОК 2: РАБОТА С ПРОМОКОДАМИ
# ==========================================

# Генерация промокода: Шаг 1 (Запрос времени жизни самого промокода)
@router.callback_query(F.data == "admin_gen_promo")
async def admin_ask_promo_days(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("У вас нет прав.")
        return

    await callback.message.edit_text(
        "⏳ Напишите, <b>через сколько дней</b> этот промокод сгорит, если его никто не активирует?\n"
        "*(Введите целое число дней, например: 7)*",
        parse_mode="HTML"
    )
    await state.set_state(AdminPromoStates.waiting_for_days)
    await callback.answer()


# Генерация промокода: Шаг 2 (Создание и запись в файл)
@router.message(AdminPromoStates.waiting_for_days)
async def admin_process_promo_days(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        days = int(message.text.strip())
        if days <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите корректное положительное число дней:")
        return

    await state.clear()

    # Генерация уникального красивого промокода (VIP-XXXX-XXXX)
    alphabet = string.ascii_uppercase + string.digits
    part1 = "".join(secrets.choice(alphabet) for _ in range(4))
    part2 = "".join(secrets.choice(alphabet) for _ in range(4))
    promo_code = f"VIP-{part1}-{part2}"

    # Расчет дат создания и окончания действия промокода
    # === Задаем Московское время (UTC+3) ===
    msk_tz = timezone(timedelta(hours=3))
    now_msk = datetime.now(msk_tz)
    end_date_msk = now_msk + timedelta(days=days)

    # Формируем структуру с пометкой MSK
    promo_data = {
        "created_at": now_msk.strftime("%Y-%m-%d %H:%M:%S") + " MSK",
        "expires_at": end_date_msk.strftime("%Y-%m-%d %H:%M:%S") + " MSK"
    }

    # Запись в файл
    all_promos = _load_promocodes()
    all_promos[promo_code] = promo_data
    _save_promocodes(all_promos)

    success_text = (
        f"✅ <b>Промокод успешно создан!</b>\n\n"
        f"🎫 Код: <code>{promo_code}</code>\n"
        f"📅 Создан: <code>{promo_data['created_at']}</code>\n"
        f"⏰ Истекает: <code>{promo_data['expires_at']}</code>\n\n"
        f"<i>Отправьте этот код пользователю. При активации он удалится из файла и выдаст вечный VIP.</i>"
    )

    # Возвращаем меню админа кнопкой под сообщением
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="⬅️ Назад в админку", callback_data="admin_back")]
    ])
    await message.answer(text=success_text, reply_markup=kb, parse_mode="HTML")


# Просмотр активных промокодов из файла
@router.callback_query(F.data == "admin_list_promo")
async def admin_view_promos(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return

    all_promos = _load_promocodes()

    if not all_promos:
        text = "📋 <b>Список промокодов пуст.</b>"
    else:
        text = "📋 <b>Активные промокоды в файле:</b>\n\n"
        for code, info in all_promos.items():
            text += f"🎫 <code>{code}</code>\n⏰ Истекает: {info['expires_at']}\n────────────────\n"

    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")]
    ])
    await callback.message.edit_text(text=text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

# ==========================================
#      БЛОК 3: СТАТИСТИКА
# ==========================================

@router.callback_query(F.data == "admin_stats")
async def admin_view_server_stats(callback: types.CallbackQuery):
    """
    Собирает детальную статистику сервера 3x-ui по каждому инбаунду
    с распределением пользователей на тарифы VIP и Limit на основе локальной БД.
    """
    if callback.from_user.id not in ADMIN_IDS:
        return

    await callback.answer("📊 Считаю тарифы VIP и Limit по инбаундам...")

    # Получаем общее число пользователей из локальной SQLite
    async with async_session() as session:
        total_users_query = select(func.count(User.id))
        total_users_res = await session.execute(total_users_query)
        db_total_users = total_users_res.scalar()

        # Вытаскиваем карту пользователей из БД {username: vpn_inbound_remark}
        # для мгновенного сопоставления тарифов без лишних запросов в цикле
        users_map_query = select(User.username, User.vpn_inbound_remark)
        users_map_res = await session.execute(users_map_query)
        db_users_tariffs = {row[0]: row[1] for row in users_map_res.all() if row[0]}

    # Запрашиваем живые данные из API 3x-ui
    inbounds_data = api.users()

    inbounds_stats_text = ""
    global_total_bytes = 0
    global_active_clients = 0
    global_online_clients = 0

    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)

    if inbounds_data.get("success"):
        for inbound in inbounds_data.get("obj", []):
            remark = inbound.get("remark", "Без названия")
            port = inbound.get("port", "???")
            protocol = inbound.get("protocol", "unknown").upper()

            inbound_bytes = 0
            inbound_active_users = 0
            inbound_online_users = 0

            # Счетчики распределения категорий внутри ЭТОГО инбаунда
            vip_in_this_inbound = 0
            limit_in_this_inbound = 0
            manual_in_this_inbound = 0

            for stat in inbound.get("clientStats", []):
                client_email = stat.get("email")
                user_traffic = stat.get("up", 0) + stat.get("down", 0)

                inbound_bytes += user_traffic
                global_total_bytes += user_traffic

                if stat.get("enable"):
                    inbound_active_users += 1
                    global_active_clients += 1

                    # Проверка онлайн-статуса (активность за последние 5 минут)
                    last_online = stat.get("lastOnline", 0)
                    if last_online > 0 and (now_ms - last_online) < 300000:
                        inbound_online_users += 1
                        global_online_clients += 1

                # Сортировка пользователя по тарифам из базы данных
                if client_email in db_users_tariffs:
                    tariff_in_db = db_users_tariffs[client_email]
                    if tariff_in_db and tariff_in_db.upper() == "VIP":
                        vip_in_this_inbound += 1
                    else:
                        limit_in_this_inbound += 1
                else:
                    # Если пользователя нет в локальной SQLite — он добавлен руками в панели
                    manual_in_this_inbound += 1

            inbound_gb = round(inbound_bytes / (1024 ** 3), 2)

            # Собираем красивый блок инбаунда
            inbounds_stats_text += (
                f"🔹 <b>Inbound: {remark}</b> (Port: <code>{port}</code> | {protocol})\n"
                f"├ 🟢 Онлайн сейчас: <code>{inbound_online_users}</code>\n"
                f"├ Активных (вкл): <code>{inbound_active_users}</code>\n"
                f"├ 👥 <b>Категории тарифов:</b>\n"
                f"│ ├ Тариф Limit: <code>{limit_in_this_inbound} чел.</code>\n"
                f"│ ├ Тариф VIP: <code>{vip_in_this_inbound} чел.</code>\n"
                f"│ └ Ручное добавление: <code>{manual_in_this_inbound} чел.</code>\n"
                f"└ Трафик порта: <code>{inbound_gb} ГБ</code>\n"
                f"──────────────────\n"
            )
    else:
        inbounds_stats_text = "❌ <i>Не удалось получить данные из панели 3x-ui</i>\n\n"

    # Переводим общий трафик в читаемый формат
    bytes_in_gb = 1024 ** 3
    bytes_in_tb = 1024 ** 4
    if global_total_bytes >= bytes_in_tb:
        global_traffic_formatted = f"<code>{round(global_total_bytes / bytes_in_tb, 2)} ТБ</code>"
    else:
        global_traffic_formatted = f"<code>{round(global_total_bytes / bytes_in_gb, 2)} ГБ</code>"

    # Вывод итогового HTML-экрана
    stats_html = (
        f"📊 <b>СВОДНАЯ СТАТИСТИКА СЕРВЕРА</b>\n\n"
        f"👥 <b>База данных сайта/бота:</b>\n"
        f"└ Всего зарегистрировано: <code>{db_total_users} чел.</code>\n\n"
        f"🌐 <b>Общие показатели VPN:</b>\n"
        f"├ Всего онлайн прямо сейчас: <code>{global_online_clients}</code>\n"
        f"├ Активных сессий на сервере: <code>{global_active_clients}</code>\n"
        f"└ Суммарный трафик сервера: {global_traffic_formatted}\n\n"
        f"📈 <b>Детализация по подключениям:</b>\n"
        f"──────────────────\n"
        f"{inbounds_stats_text}"
        f"🕒 <i>Обновлено: {datetime.now().strftime('%H:%M:%S')}</i>"
    )

    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="⬅️ Назад в админку", callback_data="admin_back")]
    ])
    await callback.message.edit_text(text=stats_html, reply_markup=kb, parse_mode="HTML")

    # Вывод итогового HTML-экрана
    stats_html = (
        f"📊 <b>СВОДНАЯ СТАТИСТИКА СЕРВЕРА</b>\n\n"
        f"👥 <b>База данных сайта/бота:</b>\n"
        f"└ Всего зарегистрировано: <code>{db_total_users} чел.</code>\n\n"
        f"🌐 <b>Общие показатели VPN:</b>\n"
        f"├ Всего онлайн прямо сейчас: <code>{global_online_clients}</code>\n"
        f"├ Активных сессий на сервере: <code>{global_active_clients}</code>\n"
        f"└ Суммарный трафик сервера: {global_traffic_formatted}\n\n"
        f"📈 <b>Детализация по подключениям:</b>\n"
        f"──────────────────\n"
        f"{inbounds_stats_text}"
        f"🕒 <i>Обновлено: {datetime.now().strftime('%H:%M:%S')}</i>"
    )

    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="⬅️ Назад в админку", callback_data="admin_back")]
    ])
    await callback.message.edit_text(text=stats_html, reply_markup=kb, parse_mode="HTML")


# ==========================================
#      БЛОК : ВОЗВРАТ В АДМИНКУ
# ==========================================

# Возврат в главное меню админки
@router.callback_query(F.data == "admin_back")
async def admin_back_to_menu(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    text = "⚙️ <b>Панель администратора VPN</b>\n\nВыберите необходимое действие:"
    await callback.message.edit_text(text=text, reply_markup=get_admin_main_keyboard(), parse_mode="HTML")
    await callback.answer()