from aiogram import Router
from .user import router as user_router
# from .admin import router as admin_router
# from .payment import router as payment_router

# Создаем единый главный роутер, в который вшиваем все остальные
router = Router()
router.include_routers(user_router)
# router.include_routers(user_router, admin_router, payment_router)