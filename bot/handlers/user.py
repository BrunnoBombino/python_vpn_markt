import bcrypt
from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from core.database import async_session
from core.models import User
from core.init_api import api  # Единый экземпляр вашего класса API
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
    await state.clear()  # Сбрасываем старые состояния, если они были
    tg_id = message.from_user.id

    async with async_session() as session:
        # Ищем пользователя по telegram_id
        query = select(User).where(User.telegram_id == tg_id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()

        if user is None:
            text = (
                f"👋 Привет, {message.from_user.full_name}!\n\n"
                f"🛡️ Для использования VPN вам необходимо зарегистрироваться или "
                f"привязать аккаунт, если вы уже регистрировались на нашем сайте."
            )
            await message.answer(text=text, reply_markup=get_start_keyboard(needs_registration=True))
        else:
            text = (
                f"🔄 С возвращением, {message.from_user.full_name}!\n\n"
                f"💻 Ваш аккаунт: `{user.email}` (Логин: `{user.email}`)\n"
                f"Управляйте подпиской через меню ниже:"
            )
            await message.answer(text=text, reply_markup=get_start_keyboard(needs_registration=False))


# ==========================================
#      БЛОК 1: РЕГИСТРАЦИЯ С НУЛЯ (FSM)
# ==========================================

@router.callback_query(F.data == "start_reg")
async def start_registration(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✍️ Шаг 1/3: Придумайте **Username**.\n"
                                     "Он будет использоваться как ваш логин на сайте и имя в панели VPN.\n"
                                     "*(Допускаются только английские буквы и цифры)*", parse_mode="Markdown")
    await state.set_state(RegistrationStates.waiting_for_username)
    await callback.answer()


@router.message(RegistrationStates.waiting_for_username)
async def process_reg_username(message: types.Message, state: FSMContext):
    username = message.text.strip().lower()

    # ⚠️ ГЛОБАЛЬНАЯ ЗАЩИТА: Проверяем, свободен ли Username в 3x-ui
    inbounds_data = vpn.users()  # Вызываем метод вашего класса
    is_taken = False
    if inbounds_data.get("success"):
        for inbound in inbounds_data.get("obj", []):
            for client in inbound.get("clientStats", []):
                if client.get("email") == username:
                    is_taken = True
                    break

    if is_taken:
        await message.answer("❌ Этот Username уже занят в системе! Придумайте другой:")
        return

    # Проверяем уникальность логина в нашей локальной базе данных
    async with async_session() as session:
        db_query = select(User).where(User.email == username)  # Т.к. username выступает логином
        db_res = await session.execute(db_query)
        if db_res.scalar_one_or_none():
            await message.answer("❌ Этот логин уже занят. Придумайте другой:")
            return

    await state.update_data(username=username)
    await message.answer("📧 Шаг 2/3: Введите ваш **Email** (нужен только для авторизации на сайте):",
                         parse_mode="Markdown")
    await state.set_state(RegistrationStates.waiting_for_email)


@router.message(RegistrationStates.waiting_for_email)
async def process_reg_email(message: types.Message, state: FSMContext):
    email = message.text.strip().lower()
    if "@" not in email or "." not in email:
        await message.answer("❌ Неверный формат Email! Пожалуйста, введите корректный адрес:")
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

    # Сохраняем пользователя
    async with async_session() as session:
        new_user = User(
            telegram_id=message.from_user.id,
            email=user_data["username"],  # Имя пользователя записываем в поле email, как договорились
            password_hash=hash_password(password)  # Хэшируем
        )
        session.add(new_user)
        await session.commit()

    await message.answer(f"🎉 Регистрация завершена успешно!\n"
                         f"👤 Ваш логин: `{user_data['username']}`\n"
                         f"Теперь вы можете использовать его на сайте и в боте.",
                         reply_markup=get_start_keyboard(needs_registration=False), parse_mode="Markdown")


# ==========================================
#      БЛОК 2: ПРИВЯЗКА АККАУНТА С САЙТА
# ==========================================

@router.callback_query(F.data == "start_link")
async def start_linking(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🔗 Введите ваш **Username**, который вы указывали при регистрации на сайте:",
                                     parse_mode="Markdown")
    await state.set_state(LinkAccountStates.waiting_for_username)
    await callback.answer()


@router.message(LinkAccountStates.waiting_for_username)
async def process_link_username(message: types.Message, state: FSMContext):
    await state.update_data(username=message.text.strip().lower())
    await message.answer("🔑 Теперь введите ваш **Пароль** от сайта:", parse_mode="Markdown")
    await state.set_state(LinkAccountStates.waiting_for_password)


@router.message(LinkAccountStates.waiting_for_password)
async def process_link_password(message: types.Message, state: FSMContext):
    password = message.text.strip()
    link_data = await state.get_data()
    await state.clear()

    async with async_session() as session:
        # Ищем аккаунт в базе по логину (username)
        query = select(User).where(User.email == link_data["username"])
        result = await session.execute(query)
        db_user = result.scalar_one_or_none()

        # Если пользователь не найден или пароль не совпал с хэшем
        if not db_user or not db_user.password_hash or not check_password(password, db_user.password_hash):
            await message.answer("❌ Неверный Username или Пароль! Привязка отменена.",
                                 reply_markup=get_start_keyboard(needs_registration=True))
            return

        # Проверяем, не привязан ли этот аккаунт уже к другому Telegram
        if db_user.telegram_id is not None:
            await message.answer("⚠️ Этот аккаунт уже привязан к другому Telegram-аккаунту!",
                                 reply_markup=get_start_keyboard(needs_registration=True))
            return

        # Всё ок, записываем telegram_id в существующую строчку сайта
        db_user.telegram_id = message.from_user.id
        await session.commit()

    await message.answer(f"✅ Аккаунт `{link_data['username']}` успешно привязан к вашему Telegram!\n"
                         f"Теперь личный кабинет синхронизирован.",
                         reply_markup=get_start_keyboard(needs_registration=False), parse_mode="Markdown")
