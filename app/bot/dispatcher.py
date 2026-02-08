from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from app.core.config import settings
from app.bot.handlers import customer, agent, commands
from app.bot.middlewares import DbSessionMiddleware

async def get_bot_dispatcher():
    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Middleware
    dp.update.middleware(DbSessionMiddleware())

    # Routers
    dp.include_router(customer.router)
    dp.include_router(commands.router)
    dp.include_router(agent.router)
    
    return bot, dp
