from aiogram import Router
from app.handlers.start import router as start_router
from app.handlers.menu import router as menu_router
from app.handlers.chat import router as chat_router
from app.handlers.premium import router as premium_router
from app.handlers.vip import router as vip_router
from app.handlers.referral import router as referral_router
from app.handlers.support import router as support_router
from app.handlers.history import router as history_router
from app.handlers.admin import router as admin_router

def get_router() -> Router:
    r = Router()
    r.include_router(start_router)
    r.include_router(menu_router)
    r.include_router(chat_router)
    r.include_router(premium_router)
    r.include_router(vip_router)
    r.include_router(referral_router)
    r.include_router(support_router)
    r.include_router(history_router)
    r.include_router(admin_router)
    return r
