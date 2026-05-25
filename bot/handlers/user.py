import bcrypt
from aiogram import types, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, or_

from datetime import datetime, timezone

from core.database import async_session
from core.models import User
from core.init_api import api  # Экземпляр вашего класса API
from bot.states import RegistrationStates, LinkAccountStates, PromoStates
from bot.keyboards.user_kb import get_start_keyboard, get_cabinet_keyboard, get_buy_keyboard, get_link_choice_keyboard

router = Router()


def hash_password(password: str) -> str:
    """Хэширование пароля перед сохранением в БД"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def check_password(password: str, hashed: str) -> bool:
    """Проверка введенного пароля с хэшем из БД"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


async def _is_subscription_active(db_user) -> bool:
    """Вспомогательная функция проверки активности подписки"""
    # Если это VIP-пользователь (expiry_date == None, а инбаунд VIP) — подписка активна всегда
    if db_user.vpn_inbound_remark == "VIP" and db_user.expiry_date is None:
        return True

    # Если дата окончания пустая или в прошлом — подписка неактивна
    now = datetime.now(timezone.utc)
    if db_user.expiry_date is None or db_user.expiry_date.replace(tzinfo=timezone.utc) < now:
        return False

    return True


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()  # Сбрасываем старые состояния
    tg_id = message.from_user.id

    async with async_session() as session:
        query = select(User).where(User.telegram_id == tg_id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()

        if user is None:
            text = (
                f"👋 Привет, {message.from_user.full_name}!\n\n"
                f"🛡️ Для использования VPN вам необходимо создать личный кабинет или "
                f"привязать аккаунт, если вы уже регистрировались на нашем сайте."
            )
            await message.answer(text=text, reply_markup=get_start_keyboard(needs_registration=True))
        else:
            text = (
                f"🔄 <b>Добро пожаловать в панель управления VPN!</b>\n\n"
                f"👤 Логин: <code>{user.username}</code>\n\n"
                f"Используйте кнопку ниже для открытия вашего Личного Кабинета ↓"
            )
            # Передаем false, чтобы отобразить кнопку Кабинета вместо регистрации
            await message.answer(text=text, reply_markup=get_start_keyboard(needs_registration=False),
                                 parse_mode="HTML")


# ==========================================
#      БЛОК 1: РЕГИСТРАЦИЯ С НУЛЯ (FSM)
# ==========================================

@router.callback_query(F.data == "start_reg")
async def start_registration(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✍️ Шаг 1/3: Придумайте **Username**.\n"
                                     "Он будет вашим логином на сайте и именем в панели 3x-ui.\n"
                                     "*(Только английские буквы и цифры)*", parse_mode="Markdown")
    await state.set_state(RegistrationStates.waiting_for_username)
    await callback.answer()


@router.message(RegistrationStates.waiting_for_username)
async def process_reg_username(message: types.Message, state: FSMContext):
    username = message.text.strip().lower()

    # Проверяем валидность символов (без пробелов и спецсимволов)
    if not username.isalnum():
        await message.answer("❌ Username может содержать только английские буквы и цифры! Попробуйте другой:")
        return

    # Глобальная проверка уникальности Username в панели 3x-ui
    inbounds_data = api.users()
    is_taken_in_panel = False
    if inbounds_data.get("success"):
        for inbound in inbounds_data.get("obj", []):
            for client in inbound.get("clientStats", []):
                if client.get("email") == username:
                    is_taken_in_panel = True
                    break

    if is_taken_in_panel:
        await message.answer("❌ Этот Username уже занят на VPN-сервере! Придумайте другой:")
        return

    # Проверяем уникальность логина в нашей локальной базе данных
    async with async_session() as session:
        db_query = select(User).where(User.username == username)
        db_res = await session.execute(db_query)
        if db_res.scalar_one_or_none():
            await message.answer("❌ Этот Username уже занят в базе сайта. Придумайте другой:")
            return

    await state.update_data(username=username)
    await message.answer("📧 Шаг 2/3: Введите ваш **Email** (нужен для авторизации на сайте):", parse_mode="Markdown")
    await state.set_state(RegistrationStates.waiting_for_email)


@router.message(RegistrationStates.waiting_for_email)
async def process_reg_email(message: types.Message, state: FSMContext):
    email = message.text.strip().lower()
    if "@" not in email or "." not in email:
        await message.answer("❌ Неверный формат Email! Пожалуйста, введите корректный адрес:")
        return

    # Проверяем уникальность email в локальной базе данных
    async with async_session() as session:
        db_query = select(User).where(User.email == email)
        db_res = await session.execute(db_query)
        if db_res.scalar_one_or_none():
            await message.answer("❌ Пользователь с таким Email уже зарегистрирован! Введите другой:")
            return

    await state.update_data(email=email)
    await message.answer("🔒 Шаг 3/3: Придумайте надежный **Пароль** для сайта:", parse_mode="Markdown")
    await state.set_state(RegistrationStates.waiting_for_password)


@router.message(RegistrationStates.waiting_for_password)
async def process_reg_password(message: types.Message, state: FSMContext):
    password = message.text.strip()
    if len(password) < 6:
        await message.answer("❌ Пароль слишком короткий (минимум 6 символов)! Придумайте другой:")
        return

    user_data = await state.get_data()
    await state.clear()

    # Сохраняем нового пользователя с заполнением всех полей
    async with async_session() as session:
        new_user = User(
            telegram_id=message.from_user.id,
            username=user_data["username"],
            email=user_data["email"],
            password_hash=hash_password(password)
        )
        session.add(new_user)
        await session.commit()

    welcome_html = (
        f"<b>🎉 Регистрация завершена успешно!</b>\n\n"
        f"👤 Ваш логин: <code>{user_data['username']}</code>\n"
        f"📧 Ваша почта: <code>{user_data['email']}</code>\n\n"
        f"⚠️ Мы не храним ваш пароль в нашей базе данных, а только его хэш!`\n\n"
        f"Теперь вы можете входить на сайт и управлять VPN через этого бота."
    )
    await message.answer(
        text=welcome_html,
        reply_markup=get_start_keyboard(needs_registration=False),
        parse_mode="HTML"
    )


# ==========================================
#      БЛОК 2: ПРИВЯЗКА АККАУНТА С САЙТА
# ==========================================

@router.callback_query(F.data == "start_link")
async def start_linking(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🔗 Введите ваш **Username** или **Email**, указанный при регистрации на сайте:",
                                     parse_mode="Markdown")
    await state.set_state(LinkAccountStates.waiting_for_username)
    await callback.answer()


@router.message(LinkAccountStates.waiting_for_username)
async def process_link_username(message: types.Message, state: FSMContext):
    await state.update_data(login_input=message.text.strip().lower())
    await message.answer("🔑 Теперь введите ваш **Пароль** от вашего аккаунта:", parse_mode="Markdown")
    await state.set_state(LinkAccountStates.waiting_for_password)


@router.message(LinkAccountStates.waiting_for_password)
async def process_link_password(message: types.Message, state: FSMContext):
    password = message.text.strip()
    link_data = await state.get_data()
    await state.clear()

    login_input = link_data["login_input"]

    async with async_session() as session:
        # Ищем запись, где введенная строка совпадает ЛИБО с username, ЛИБО с email
        query = select(User).where(
            or_(
                User.username == login_input,
                User.email == login_input
            )
        )
        result = await session.execute(query)
        db_user = result.scalar_one_or_none()

        # Проверка существования аккаунта и валидности пароля
        if not db_user or not db_user.password_hash or not check_password(password, db_user.password_hash):
            await message.answer("❌ Неверный логин/email или пароль! Привязка отменена.",
                                 reply_markup=get_start_keyboard(needs_registration=True))
            return

        # Проверяем, не привязан ли этот аккаунт уже к кому-то в Telegram
        if db_user.telegram_id is not None:
            await message.answer("⚠️ Этот аккаунт на сайте уже привязан к какому-то Telegram-профилю!",
                                 reply_markup=get_start_keyboard(needs_registration=True))
            return

        # Записываем telegram_id текущего пользователя в существующую строку
        db_user.telegram_id = message.from_user.id
        await session.commit()

        success_username = db_user.username

    success_html = (
        f"✅ Аккаунт <code>{success_username}</code> успешно синхронизирован с вашим Telegram!\n"
        f"Теперь ваш личный кабинет полностью объединен."
    )

    await message.answer(
        text=success_html,
        reply_markup=get_start_keyboard(needs_registration=False),
        parse_mode="HTML"
    )


# ==========================================
#      БЛОК 3: ПОЛУЧЕНИЕ ССЫЛКИ ПОДПИСКИ
# ==========================================

# Открытие меню выбора типа ссылки
@router.callback_query(F.data == "choose_link_type")
async def menu_choose_link_type(callback: types.CallbackQuery):
    text = (
        "🚀 <b>Выбор типа подключения к VPN</b>\n\n"
        "Разные приложения поддерживают разные форматы ссылок:\n\n"
        "🔄 <b>Ссылка-Подписка (HTTPS):</b> Рекомендуется для Hiddifi Next и Streisand. "
        "Она автоматически обновляет ключи и показывает остаток дней прямо внутри приложения.\n\n"
        "🔑 <b>Прямой VLESS ключ:</b> Используется для AmneziaVPN, v2rayNG и старых клиентов. "
    )
    await callback.message.edit_text(text=text, reply_markup=get_link_choice_keyboard(), parse_mode="HTML")
    await callback.answer()


# Сценарий 1: Выдача Ссылки-Подписки (HTTPS)
@router.callback_query(F.data == "get_link_sub")
async def handle_get_sub_link(callback: types.CallbackQuery):
    tg_id = callback.from_user.id

    async with async_session() as session:
        query = select(User).where(User.telegram_id == tg_id)
        result = await session.execute(query)
        db_user = result.scalar_one_or_none()

    if not db_user:
        await callback.message.answer("❌ Аккаунт не найден.")
        return

    # Проверяем подписку
    if not await _is_subscription_active(db_user):
        text = "⚠️ <b>Доступ ограничен</b>\n\nУ вас нет активной подписки. Пожалуйста, приобретите тариф."
        await callback.message.edit_text(text=text, reply_markup=get_cabinet_keyboard(), parse_mode="HTML")
        return

    await callback.answer("⏳ Генерирую ссылку подписки...")

    # === СИНХРОНИЗАЦИЯ С БАЗОЙ ДАННЫХ ДЛЯ НОВОГО КЛИЕНТА В ПАНЕЛИ ===
    if not db_user.vpn_uuid or not db_user.vpn_sub_id:
        # 1. Определяем инбаунд: берем из БД, либо "limit" если поле пустое
        target_inbound = db_user.vpn_inbound_remark if db_user.vpn_inbound_remark else "limit"

        # 2. Рассчитываем дни: сколько дней осталось от текущего момента до expiry_date
        if target_inbound.upper() == "VIP" or db_user.expiry_date is None:
            days_to_grant = 36500  # Для VIP/безлимита даем 100 лет (в API сработает сброс в 0)
        else:
            now = datetime.now(timezone.utc)
            remaining_time = db_user.expiry_date.replace(tzinfo=timezone.utc) - now
            days_to_grant = max(1, remaining_time.days)  # Минимум 1 день, чтобы API не выдало ошибку

        # Создаем пользователя в 3x-ui со СТРОГО ЕГО данными из базы
        new_vpn_data = api.add_user(
            username=db_user.username,
            remark=target_inbound,
            days=days_to_grant,
            telegram_id=tg_id
        )

        if new_vpn_data:
            async with async_session() as session:
                query = select(User).where(User.telegram_id == tg_id)
                res = await session.execute(query)
                u = res.scalar_one()
                u.vpn_uuid = new_vpn_data.get("uuid")
                u.vpn_sub_id = new_vpn_data.get("sub_id", new_vpn_data.get("subId"))
                u.vpn_inbound_remark = target_inbound
                await session.commit()
            # Перечитываем обновленный subId
            db_user_username = db_user.username
        else:
            await callback.message.edit_text("❌ Ошибка синхронизации ключей с серверов VPN.",
                                             reply_markup=get_link_choice_keyboard(), parse_mode="HTML")
            return
    else:
        db_user_username = db_user.username

    # Получаем чистый HTTPS URL подписки
    sub_link = api.get_subscription_link(db_user_username)

    success_text = (
        f"🔄 <b>Ваша ссылка-подписка готовa!</b>\n\n"
        f"<code>{sub_link}</code>\n\n"
        f"👇 <i>Нажмите на текст выше, чтобы скопировать. Настройка для <b>Hiddifi / Streisand</b>.</i>"
    )
    await callback.message.edit_text(text=success_text, reply_markup=get_link_choice_keyboard(), parse_mode="HTML")


# Сценарий 2: Выдача Прямого VLESS Ключа (vless://...)
@router.callback_query(F.data == "get_link_vless")
async def handle_get_vless_link(callback: types.CallbackQuery):
    tg_id = callback.from_user.id

    async with async_session() as session:
        query = select(User).where(User.telegram_id == tg_id)
        result = await session.execute(query)
        db_user = result.scalar_one_or_none()

    if not db_user:
        await callback.message.answer("❌ Аккаунт не найден.")
        return

    if not await _is_subscription_active(db_user):
        text = "⚠️ <b>Доступ ограничен</b>\n\nУ вас нет active-подписки. Пожалуйста, приобретите тариф."
        await callback.message.edit_text(text=text, reply_markup=get_cabinet_keyboard(), parse_mode="HTML")
        return

    await callback.answer("⏳ Генерирую прямой VLESS ключ...")

    # === СИНХРОНИЗАЦИЯ С БАЗОЙ ДАННЫХ ДЛЯ НОВОГО КЛИЕНТА В ПАНЕЛИ ===
    if not db_user.vpn_uuid:
        target_inbound = db_user.vpn_inbound_remark if db_user.vpn_inbound_remark else "limit"

        if target_inbound.upper() == "VIP" or db_user.expiry_date is None:
            days_to_grant = 36500
        else:
            now = datetime.now(timezone.utc)
            remaining_time = db_user.expiry_date.replace(tzinfo=timezone.utc) - now
            days_to_grant = max(1, remaining_time.days)

        new_vpn_data = api.add_user(
            username=db_user.username,
            remark=target_inbound,
            days=days_to_grant,
            telegram_id=tg_id
        )

        if new_vpn_data:
            async with async_session() as session:
                query = select(User).where(User.telegram_id == tg_id)
                res = await session.execute(query)
                u = res.scalar_one()
                u.vpn_uuid = new_vpn_data.get("uuid")
                u.vpn_sub_id = new_vpn_data.get("sub_id", new_vpn_data.get("subId"))
                u.vpn_inbound_remark = target_inbound
                await session.commit()
            db_user_username = db_user.username
        else:
            await callback.message.edit_text("❌ Ошибка синхронизации ключей с сервером VPN.",
                                             reply_markup=get_link_choice_keyboard(), parse_mode="HTML")
            return
    else:
        db_user_username = db_user.username

    # Получаем прямую vless://... строку
    vless_link = api.get_client_link(db_user_username)

    success_text = (
        f"🔑 <b>Ваш прямой VLESS ключ готов!</b>\n\n"
        f"<code>{vless_link}</code>\n\n"
        f"👇 <i>Нажмите на текст выше, чтобы скопировать. Настройка для <b>AmneziaVPN / v2rayNG</b>.</i>"
    )
    await callback.message.edit_text(text=success_text, reply_markup=get_link_choice_keyboard(), parse_mode="HTML")


# ==========================================
#      БЛОК 4: ЛИЧНЫЙ КАБИНЕТ
# ==========================================

@router.callback_query(F.data == "open_cabinet")
async def open_cabinet(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    text = "🗄️ <b>Личный кабинет пользователя</b>\n\nВыберите интересующий вас раздел:"
    await callback.message.edit_text(text=text, reply_markup=get_cabinet_keyboard(), parse_mode="HTML")
    await callback.answer()

# ==========================================
#      БЛОК 5: МЕНЮ ПОКУПКИ ПОДПИСКИ
# ==========================================

@router.callback_query(F.data == "buy_menu")
async def open_buy_menu(callback: types.CallbackQuery):
    text = "💳 <b>Управление подпиской и тарифами</b>\n\nВыберите подходящий вариант или активируйте промокод:"
    await callback.message.edit_text(text=text, reply_markup=get_buy_keyboard(), parse_mode="HTML")
    await callback.answer()

# ==========================================
#      БЛОК 6: ПОМОЩЬ И ИНСТРУКЦИИ
# ==========================================

@router.callback_query(F.data == "help_info")
async def show_help_info(callback: types.CallbackQuery):
    help_text = (
        "❓ <b>Инструкции по настройке и подключению</b>\n\n"
        "Для работы с нашим VPN мы рекомендуем использовать приложение <b>Hiddify Next</b> или <b>Streisand</b>.\n\n"
        "🍏 <b>Для iPhone (iOS):</b>\n"
        "1. Установите бесплатное приложение <b>Streisand</b> или <b>Hiddify</b> из AppStore.\n"
        "2. Скопируйте ссылку подписки из раздела 'Информация об аккаунте'.\n"
        "3. В приложении нажмите знак [+] ➡️ 'Импортировать из буфера'.\n\n"
        "🤖 <b>Для Android:</b>\n"
        "1. Скачайте приложение <b>Hiddify Next</b> или <b>v2rayNG</b> из Google Play.\n"
        "2. Скопируйте ваш индивидуальный URL-адрес подписки.\n"
        "3. Импортируйте профиль и нажмите круглую кнопку запуска по центру."
    )
    # Возвращаем пользователя обратно в ЛК
    kb = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="⬅️ Назад в кабинет", callback_data="open_cabinet")]
    ])
    await callback.message.edit_text(text=help_text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

# ==========================================
#      БЛОК 7: ВВОД ПРОМОКОДА
# ==========================================

# Включение машины состояний FSM
@router.callback_query(F.data == "enter_promo")
async def ask_for_promo(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🎫 <b>Активация промокода</b>\n\nВведите ваш секретный промокод в ответном сообщении:", parse_mode="HTML")
    await state.set_state(PromoStates.waiting_for_code)
    await callback.answer()


# Проверка и перевод в VIP-безлимит
@router.message(PromoStates.waiting_for_code)
async def process_promo_code(message: types.Message, state: FSMContext):
    promo_entered = message.text.strip().upper()
    await state.clear()

    # Валидные промокоды
    VALID_PROMO_CODES = ["FREEVIP", "PROMO2026", "VPNUNLIMITED"]

    if promo_entered not in VALID_PROMO_CODES:
        await message.answer("❌ <b>Ошибка:</b> Неверный или устаревший промокод!",
                             reply_markup=get_buy_keyboard(), parse_mode="HTML")
        return

    tg_id = message.from_user.id

    # 1. Получаем пользователя из локальной БД
    async with async_session() as session:
        query = select(User).where(User.telegram_id == tg_id)
        result = await session.execute(query)
        db_user = result.scalar_one_or_none()

    if not db_user:
        await message.answer("❌ Пользователь не найден в базе данных.")
        return

    # Целевой инбаунд для промокода
    target_vip_remark = "VIP"
    transfer_success = False

    # 2. ПРОВЕРКА: Создан ли пользователь в панели 3x-ui?
    # Если vpn_uuid пустой, значит пользователя на сервере VPN ЕЩЕ НЕТ
    if not db_user.vpn_uuid or not db_user.vpn_sub_id:
        print(f"⭐ Новый пользователь {db_user.username}. Создаю аккаунт сразу в VIP...")

        # Вызываем метод прямого создания пользователя сразу в инбаунде VIP на 100 лет (безлимит)
        new_vpn_data = api.add_user(
            username=db_user.username,
            remark=target_vip_remark,
            days=36500,  # 100 лет (панель примет это как долгосрочный безлимит)
        )
        print(new_vpn_data)

        if new_vpn_data:
            # Обновляем локальную базу данных SQLite, записывая новые ключи
            async with async_session() as session:
                query = select(User).where(User.telegram_id == tg_id)
                res = await session.execute(query)
                user_to_update = res.scalar_one()

                # Используем .get(), проверяя оба варианта написания ключа (sub_id и subId)
                user_to_update.vpn_uuid = new_vpn_data.get("uuid")
                user_to_update.vpn_sub_id = new_vpn_data.get("subid", new_vpn_data.get("subId"))

                user_to_update.vpn_inbound_remark = target_vip_remark
                user_to_update.expiry_date = None  # NULL в базе (вечный тариф)
                await session.commit()

            transfer_success = True

    # 3. Если пользователь УЖЕ СУЩЕСТВОВАЛ в панели, делаем стандартный безопасный перенос
    else:
        print(f"🔄 Существующий пользователь {db_user.username}. Переношу из {db_user.vpn_inbound_remark} в VIP...")
        current_remark = db_user.vpn_inbound_remark if db_user.vpn_inbound_remark else "Limit"

        # Наш безопасный метод переноса с бэкапом
        transfer_success = api.change_inbound(
            username=db_user.username,
            current_remark=current_remark,
            new_remark=target_vip_remark
        )

        if transfer_success:
            # Обновляем локальную базу данных SQLite: меняем инбаунд на VIP
            async with async_session() as session:
                query = select(User).where(User.telegram_id == tg_id)
                res = await session.execute(query)
                user_to_update = res.scalar_one()

                user_to_update.vpn_inbound_remark = target_vip_remark
                user_to_update.expiry_date = None  # Сбрасываем ограничение времени в локальной БД
                await session.commit()

    # 4. Выводим результат пользователю
    if transfer_success:
        success_text = (
            "⭐ <b>Промокод успешно активирован!</b>\n\n"
            "Поздравляем! Вам предоставлен бессрочный <b>VIP-Безлимит</b>.\n"
            "Все ограничения по трафику и времени полностью сняты.\n\n"
            "<i>Зайдите в раздел 'Информация об аккаунте', чтобы получить вашу новую ссылку подписки!</i>"
        )
        await message.answer(text=success_text, reply_markup=get_cabinet_keyboard(), parse_mode="HTML")
    else:
        await message.answer("❌ <b>Техническая ошибка:</b> Не удалось активировать промокод на сервере. "
                             "Пожалуйста, попробуйте позже.", reply_markup=get_buy_keyboard(), parse_mode="HTML")


# Кнопка возврата на главный экран
@router.callback_query(F.data == "back_to_main")
async def back_to_main_menu(callback: types.CallbackQuery):
    text = "📋 <b>Главное меню управления VPN</b>\n\nИспользуйте кнопку ниже для входа в кабинет:"
    await callback.message.edit_text(text=text, reply_markup=get_start_keyboard(needs_registration=False),
                                     parse_mode="HTML")
    await callback.answer()