from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_start_keyboard(needs_registration: bool) -> InlineKeyboardMarkup:
    """Кнопки первого экрана при старте"""
    buttons = []
    if needs_registration:
        buttons.append([InlineKeyboardButton(text="📝 Создать новый аккаунт", callback_data="start_reg")])
        buttons.append([InlineKeyboardButton(text="🔗 Привязать аккаунт с сайта", callback_data="start_link")])
    else:
        buttons.append([InlineKeyboardButton(text="👤 Личный кабинет", callback_data="open_cabinet")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_cabinet_keyboard() -> InlineKeyboardMarkup:
    """Интерфейс внутри личного кабинета"""
    buttons = [
        [InlineKeyboardButton(text="📊 Информация об аккаунте", callback_data="user_profile")],
        [InlineKeyboardButton(text="🚀 Получить VPN ссылки", callback_data="choose_link_type")],
        [InlineKeyboardButton(text="💳 Покупка / Продление подписки", callback_data="buy_menu")],
        [InlineKeyboardButton(text="❓ Помощь по подключению", callback_data="help_info")],
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_link_choice_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора типа ссылки для подключения"""
    buttons = [
        [InlineKeyboardButton(text="🔄 Ссылка-Подписка (Hiddifi / Streisand)", callback_data="get_link_sub")],
        [InlineKeyboardButton(text="🔑 Прямой VLESS ключ (Amnezia / v2rayNG)", callback_data="get_link_vless")],
        [InlineKeyboardButton(text="⬅️ Назад в кабинет", callback_data="open_cabinet")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_buy_keyboard() -> InlineKeyboardMarkup:
    """Интерфейс выбора тарифов и промокодов"""
    buttons = [
        [InlineKeyboardButton(text="🍏 Тариф 30 дней", callback_data="buy_tariff_30")],
        [InlineKeyboardButton(text="🍎 Тариф 180 дней", callback_data="buy_tariff_180")],
        [InlineKeyboardButton(text="🍍 Тариф 365 дней", callback_data="buy_tariff_365")],
        [InlineKeyboardButton(text="🎫 Ввести промокод", callback_data="enter_promo")],
        [InlineKeyboardButton(text="⬅️ Назад в кабинет", callback_data="open_cabinet")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)