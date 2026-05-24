import bcrypt
from aiogram import types, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, or_

from core.database import async_session
from core.models import User
from core.init_api import api  # Экземпляр вашего класса API
from bot.states import RegistrationStates, LinkAccountStates
from bot.keyboards.user_kb import get_start_keyboard

router = Router()


def hash_password(password: str) -> str:
    """Хэширование пароля перед сохранением в БД"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')


def check_password(password: str, hashed: str) -> bool:
    """Проверка введенного пароля с хэшем из БД"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


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
                f"🔄 С возвращением, {message.from_user.full_name}!\n\n"
                f"👤 Логин: `{user.username}`\n"
                f"📧 Почта: `{user.email}`\n\n"
                f"Управляйте подпиской через меню ниже:"
            )
            await message.answer(text=text, reply_markup=get_start_keyboard(needs_registration=False))


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

    # 1. Проверяем валидность символов (без пробелов и спецсимволов)
    if not username.isalnum():
        await message.answer("❌ Username может содержать только английские буквы и цифры! Попробуйте другой:")
        return

    # 2. Глобальная проверка уникальности Username в панели 3x-ui
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

    # 3. Проверяем уникальность логина в нашей локальной базе данных
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

    await message.answer(f"🎉 Регистрация завершена успешно!\n\n"
                         f"👤 Ваш логин: `{user_data['username']}`\n"
                         f"📧 Ваша почта: `{user_data['email']}`\n\n"
                         f"⚠️ Мы не храним ваш пароль в нашей базе данных, а только его хэш!`\n\n"
                         f"Теперь вы можете входить на сайт и управлять VPN через этого бота.",
                         reply_markup=get_start_keyboard(needs_registration=False), parse_mode="Markdown")


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

    await message.answer(f"✅ Аккаунт `{success_username}` успешно синхронизирован с вашим Telegram!\n"
                         f"Теперь ваш личный кабинет полностью объединен.",
                         reply_markup=get_start_keyboard(needs_registration=False), parse_mode="Markdown")
