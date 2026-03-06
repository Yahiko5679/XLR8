import os
from dotenv import load_dotenv

load_dotenv()

# ── Bot ──────────────────────────────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 0))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", 0))

# ── MongoDB (singleton: COSMICBOTZ) ──────────────────────────────────────────
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = "COSMICBOTZ"          # fixed singleton instance name

# ── TMDB ─────────────────────────────────────────────────────────────────────
TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"

# ── Link Revoke ───────────────────────────────────────────────────────────────
AUTO_REVOKE_MINUTES = int(os.getenv("AUTO_REVOKE_MINUTES", 30))

# ── Webhook (Render) ─────────────────────────────────────────────────────────
PORT = int(os.getenv("PORT", 8080))
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")   # e.g. https://your-app.onrender.com
