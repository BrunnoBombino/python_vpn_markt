from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_start_keyboard(needs_registration: bool) -> InlineKeyboardMarkup:
    """Генерирует кнопки для стартового меню"""
    buttons = []

    if needs_registration:
        buttons.append([InlineKeyboardButton(text="📝 Создать новый аккаунт", callback_data="start_reg")])
        buttons.append([InlineKeyboardButton(text="🔗 Привязать существующий аккаунт", callback_data="start_link")])
    else:
        buttons.append([InlineKeyboardButton(text="👤 Мой Личный Кабинет", callback_data="user_profile")])
        buttons.append([InlineKeyboardButton(text="🚀 Получить VPN ссылку", callback_data="get_vpn_link")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)
