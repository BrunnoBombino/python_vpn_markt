from fastapi import APIRouter
# from .auth import router as auth_router
# from .cabinet import router as cabinet_router

# Главный веб-роутер проекта
api_router = APIRouter()

# Подключаем модули с красивыми префиксами
# api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
# api_router.include_router(cabinet_router, prefix="/cabinet", tags=["Cabinet"])
