import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, APIRouter
from app.core.config import settings
from app.core.logging import setup_logging
from app.bot.dispatcher import get_bot_dispatcher
from app.db.session import engine

# Setup Logging
setup_logging()
logger = logging.getLogger(__name__)

# Global Bot/DP refs for shutdown
bot_ref = None
dp_ref = None
polling_task = None

async def start_bot():
    global bot_ref, dp_ref
    bot, dp = await get_bot_dispatcher()
    bot_ref = bot
    dp_ref = dp
    
    # Drop pending updates to avoid potential issues on restart (optional)
    await bot.delete_webhook(drop_pending_updates=True)
    
    logger.info("🤖 Starting Bot Polling...")
    try:
        await dp.start_polling(bot)
    except asyncio.CancelledError:
        logger.info("🛑 Bot Polling Cancelled")
    finally:
        await bot.session.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 API Startup")
    
    # Start Bot in Background Task
    global polling_task
    polling_task = asyncio.create_task(start_bot())
    
    yield
    
    # Shutdown
    logger.info("🛑 API Shutdown")
    if dp_ref:
        await dp_ref.stop_polling()
    if polling_task:
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass
            
    # Close DB Engine
    await engine.dispose()

def create_app() -> FastAPI:
    app = FastAPI(title="Digital Support Bot API", lifespan=lifespan, version="1.0.0")

    # Health Check
    @app.get("/health")
    async def health_check():
        return {"status": "ok"}
        
    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
