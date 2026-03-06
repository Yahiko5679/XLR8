# 🤖 Auto Filter CosmicBotz v2

Auto-post filter bot for Anime, TV Shows & Movies.  
TMDB · Letter index · Auto-revoke invite links · Group verification · Webhook mode

---

## ⚙️ Setup (Local)

```bash
pip install -r requirements.txt
cp .env.example .env   # fill in your values
python bot.py
```

---

## 🚀 Render Deployment

1. Push to GitHub
2. Create **New Web Service** on Render → connect repo
3. Render auto-detects `render.yaml`
4. Set these env vars in **Render Dashboard**:

| Variable | Value |
|---|---|
| `BOT_TOKEN` | From @BotFather |
| `OWNER_ID` | Your Telegram user ID |
| `MONGO_URI` | MongoDB Atlas URI |
| `TMDB_API_KEY` | From themoviedb.org |
| `WEBHOOK_URL` | `https://your-app-name.onrender.com` |

5. Set **Health Check Path** → `/health` in Render service settings
6. Deploy!

> **Webhook flow:** Render runs the aiohttp server → Telegram POSTs updates to `/webhook` → no polling needed. The `/health` GET endpoint keeps Render from restarting the service.

---

## 🌐 Group System

| Step | What happens |
|---|---|
| Bot added to group | Sends welcome message, owner notified in DM |
| Owner sends `/verify` in group | All features unlocked |
| Unverified group | Only `/start` responds, all else silently ignored |
| `/verifygroup GROUP_ID` (DM) | Verify remotely from DM |
| `/groups` | Owner sees all groups + pending list |
| `/unverify` | Revoke group access |

---

## 📋 Commands

### Owner (DM only)
`/addslot` · `/slots` · `/removeslot` · `/addcontent` · `/addadmin` · `/removeadmin` · `/admins` · `/setrevoke` · `/settings` · `/groups` · `/verifygroup`

### Admin (DM + verified groups)
`/addcontent` · `/slots` · `/stats` · `/verify`

### All users (verified groups + DM)
Send letter `A–Z` → index browse  
Send title name → search  
Tap result → channel post  
Tap Watch/Download → timed invite link

---

## 📁 Structure
```
auto_filter_cosmicbotz/
├── bot.py                    # Webhook entry point (aiohttp + aiogram)
├── config.py                 # Env config (DB_NAME = COSMICBOTZ)
├── render.yaml               # Render deploy config
├── requirements.txt
├── .env.example
├── database/
│   ├── mongo.py              # Singleton Motor client → COSMICBOTZ
│   ├── filters.py            # Content index CRUD
│   ├── slots.py              # Slots, admins, settings
│   ├── posts.py              # Post + invite link tracking
│   └── groups.py             # Group verification
├── handlers/
│   ├── start.py              # /start /help /stats
│   ├── admin.py              # Slot & admin management
│   ├── post.py               # /addcontent TMDB wizard
│   ├── filter.py             # Letter/search filter
│   └── group.py              # Group join/verify lifecycle
├── keyboards/
│   └── inline.py             # All inline keyboards
├── services/
│   ├── tmdb.py               # TMDB API (anime, tv, movie)
│   ├── caption.py            # Caption builder
│   └── link_gen.py           # Invite link + revoke
├── middlewares/
│   └── auth.py               # Owner/admin/group verification checks
└── utils/
    └── scheduler.py          # APScheduler — auto-revoke expired links
```

---

## 🗄️ MongoDB — COSMICBOTZ
| Collection | Purpose |
|---|---|
| `filters` | Anime/movie/tvshow index |
| `slots` | Channel slots |
| `admins` | Admin user IDs |
| `posts` | Posted messages + invite link expiry (TTL indexed) |
| `settings` | Per-owner settings |
| `groups` | Group verification records |
