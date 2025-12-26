from aiogram import Router
from .commands import router as commands_router
from .callbacks import router as callbacks_router
from .ai_handler import router as ai_router

router = Router()

# TARTIB: Oldin buyruqlar, keyin tugmalar, eng oxirida AI tahlilchisi
router.include_router(commands_router)
router.include_router(callbacks_router)
router.include_router(ai_router)
