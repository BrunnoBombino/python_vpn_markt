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
    now = datetime.now(timezone.utc)
    end_date = now + timedelta(days=days)

    # Структура данных промокода
    promo_data = {
        "created_at": now.strftime("%Y-%m-%d %H:%M:%S") + " UTC",
        "expires_at": end_date.strftime("%Y-%m-%d %H:%M:%S") + " UTC"
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