from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """Главная клавиатура админ-панели"""
    buttons = [
        [InlineKeyboardButton(text="🔍 Найти пользователя", callback_data="admin_search_user")],
        [InlineKeyboardButton(text="🎫 Сгенерировать промокод VIP", callback_data="admin_gen_promo")],
        [InlineKeyboardButton(text="📋 Список активных промокодов", callback_data="admin_list_promo")],
        [InlineKeyboardButton(text="📊 Статистика сервера", callback_data="admin_stats")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_user_manage_keyboard(username: str, is_enabled: bool) -> InlineKeyboardMarkup:
    """Кнопки управления конкретным пользователем"""
    block_text = "🔒 Заблокировать" if is_enabled else "🔓 Разблокировать"
    buttons = [
        [InlineKeyboardButton(text="➕ Выдать 5 дней", callback_data=f"adm_add_5:{username}")],
        [InlineKeyboardButton(text=block_text, callback_data=f"adm_toggle_block:{username}")],
        [InlineKeyboardButton(text="🔄 Сбросить трафик на 0", callback_data=f"adm_reset_tr:{username}")],
        [InlineKeyboardButton(text="⬅️ В админку", callback_data="admin_back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)