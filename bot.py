import os
import sys
import logging
from aiohttp import web

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# ─────────────────────────────────────────────
# Fix working directory (important for Render)
# ─────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _ROOT)
os.chdir(_ROOT)

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
from config import BOT_TOKEN, OWNER_ID
from database.mongo import connect_db, close_db
from middlewares.auth import AuthMiddleware
from handlers import start, admin, post
from handlers import filter as filter_handler
from handlers import group
from utils.scheduler import setup_scheduler, stop_scheduler

PORT = int(os.environ.get("PORT", 8080))
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")
WEBHOOK_PATH = "/webhook"

if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN is missing!")

if not WEBHOOK_URL:
    raise ValueError("❌ WEBHOOK_URL is missing! Set it in Render env vars.")

# ─────────────────────────────────────────────
# Logging
# ─────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
LOGGER = logging.getLogger("cosmicbotz")

# ─────────────────────────────────────────────
# Bot & Dispatcher
# ─────────────────────────────────────────────
bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)

dp = Dispatcher()

# ── Middleware ────────────────────────────────
dp.message.middleware(AuthMiddleware())
dp.callback_query.middleware(AuthMiddleware())
dp.my_chat_member.middleware(AuthMiddleware())

# ── Routers (order matters — specific before catch-all) ──────────────────────
dp.include_router(group.router)           # group join/leave/verify
dp.include_router(start.router)           # /start /help /stats
dp.include_router(admin.router)           # slots, admins, settings
dp.include_router(post.router)            # /addcontent TMDB wizard
dp.include_router(filter_handler.router)  # letter/search — MUST be last

LOGGER.info("✅ All routers loaded")

# ─────────────────────────────────────────────
# Startup
# ─────────────────────────────────────────────
async def on_startup(bot: Bot):
    await connect_db()
    setup_scheduler(bot)

    webhook = f"{WEBHOOK_URL.rstrip('/')}{WEBHOOK_PATH}"
    await bot.set_webhook(url=webhook, drop_pending_updates=True)
    LOGGER.info(f"✅ Webhook set → {webhook}")

    # Notify owner
    try:
        await bot.send_message(
            chat_id=OWNER_ID,
            text="<b><blockquote>🤖 Auto Filter CosmicBotz Started ✅</blockquote></b>",
        )
    except Exception as e:
        LOGGER.warning(f"Could not notify owner {OWNER_ID}: {e}")


# ─────────────────────────────────────────────
# Shutdown (DO NOT delete webhook in production)
# ─────────────────────────────────────────────
async def on_shutdown(bot: Bot):
    LOGGER.info("⛔ Shutting down...")
    stop_scheduler()
    await close_db()
    await bot.session.close()
    LOGGER.info("✅ Bot session closed.")


# ─────────────────────────────────────────────
# Main App
# ─────────────────────────────────────────────
def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    app = web.Application()

    # Root endpoint
    app.router.add_get("/", lambda r: web.Response(text="Auto Filter CosmicBotz Running!"))

    # Health check (set this as Health Check URL in Render dashboard)
    app.router.add_get("/health", lambda r: web.Response(text="OK"))

    # Allow GET on webhook path (prevents 405 → Render restart issue)
    app.router.add_get(WEBHOOK_PATH, lambda r: web.Response(text="Webhook Alive"))

    # Telegram webhook handler (POST)
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)

    LOGGER.info(f"🌐 Starting on port {PORT}")
    web.run_app(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
