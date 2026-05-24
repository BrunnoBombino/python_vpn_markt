from aiogram.fsm.state import StatesGroup, State

class RegistrationStates(StatesGroup):
    waiting_for_username = State()  # Ждем логин
    waiting_for_email = State()     # Ждем почту
    waiting_for_password = State()  # Ждем пароль

class LinkAccountStates(StatesGroup):
    waiting_for_username = State()  # Ждем логин для привязки
    waiting_for_password = State()  # Ждем пароль для привязки

class PromoStates(StatesGroup):
    waiting_for_code = State()  # Ожидание ввода промокода текстом