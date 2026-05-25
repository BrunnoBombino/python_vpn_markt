from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage
from core.auth import TOKEN


PROXY_URL = "http://127.0.0.1:12334"
session = AiohttpSession(proxy=PROXY_URL)
bot = Bot(token=TOKEN,  session=session, default=DefaultBotProperties(parse_mode="HTML"))

# MemoryStorage нужен для работы машины состояний (FSM) при вводе данных
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
