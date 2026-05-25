from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура админ-панели"""
    buttons = [
        [InlineKeyboardButton(text="🎫 Сгенерировать промокод VIP", callback_data="admin_gen_promo")],
        [InlineKeyboardButton(text="📋 Список активных промокодов", callback_data="admin_list_promo")],
        [InlineKeyboardButton(text="📊 Статистика сервера", callback_data="admin_stats")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
