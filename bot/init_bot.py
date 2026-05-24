from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from core.auth import TOKEN

# Создаем объекты один раз здесь
bot = Bot(token=TOKEN)

# MemoryStorage нужен для работы машины состояний (FSM) при вводе данных
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
