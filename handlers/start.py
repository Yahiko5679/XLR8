import random
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from aiogram.enums import ChatType

from database import CosmicBotz
from config import START_PICS

router = Router()


def _owner_text(name: str) -> str:
    return (
        f"👋 Welcome back, <b>{name}</b>!\n\n"
        "🤖 <b>Auto Filter CosmicBotz</b> — Owner Panel\n\n"
        "<b>📢 Slots:</b>\n"
        "/addslot · /slots · /removeslot\n\n"
        "<b>🎬 Content:</b>\n"
        "/addcontent\n\n"
        "<b>👥 Admins:</b>\n"
        "/addadmin · /removeadmin · /admins\n\n"
        "<b>🌐 Groups:</b>\n"
        "/groups · /verifygroup\n\n"
        "<b>⚙️ Settings:</b>\n"
        "/setrevoke · /settings · /stats"
    )


def _admin_text(name: str) -> str:
    return (
        f"👋 Hello, <b>{name}</b>!\n\n"
        "🤖 <b>Auto Filter CosmicBotz</b> — Admin Panel\n\n"
        "/addcontent · /slots · /stats\n\n"
        "Send a letter (A–Z) to browse the index."
    )


def _user_text(name: str) -> str:
    return (
        f"👋 Hello, <b>{name}</b>!\n\n"
        "🤖 <b>Auto Filter CosmicBotz</b>\n\n"
        "Send a <b>single letter</b> to browse the index.\n"
        "Example: send <code>N</code> → Naruto, Noir…\n\n"
        "Or type a <b>title</b> to search directly."
    )


def _group_verified_text() -> str:
    return (
        "🤖 <b>Auto Filter CosmicBotz</b> is active here!\n\n"
        "Send a <b>letter</b> (A–Z) to browse the index.\n"
        "Or type a <b>title</b> to search."
    )


def _group_unverified_text() -> str:
    return (
        "🤖 <b>Auto Filter CosmicBotz</b>\n\n"
        "⚠️ This group is <b>not verified</b> yet.\n"
        "An owner or admin must send /verify to unlock all features."
    )


async def _send_start(message: Message, text: str):
    """
    Try to send a random image from START_PICS with caption.
    Falls back to plain text if list is empty or sending fails.
    """
    if START_PICS:
        photo = random.choice(START_PICS)
        try:
            await message.answer_photo(
                photo=photo,
                caption=text,
                parse_mode="HTML"
            )
            return
        except Exception:
            pass  # fall through to text fallback

    # Fallback — plain text
    await message.answer(text, parse_mode="HTML")


# ── /start ────────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(
    message: Message,
    is_owner: bool = False,
    is_admin: bool = False,
    **kwargs
):
    name       = message.from_user.full_name
    is_private = message.chat.type == ChatType.PRIVATE

    if is_private:
        if is_owner:
            text = _owner_text(name)
        elif is_admin:
            text = _admin_text(name)
        else:
            text = _user_text(name)
    else:
        verified = await CosmicBotz.is_group_verified(message.chat.id)
        text = _group_verified_text() if verified else _group_unverified_text()

    await _send_start(message, text)


# ── /help ─────────────────────────────────────────────────────────────────────

@router.message(Command("help"))
async def cmd_help(message: Message, **kwargs):
    await message.answer(
        "📖 <b>How to use:</b>\n\n"
        "• Send a <b>letter</b> (A–Z) to see all indexed titles.\n"
        "• Send a <b>title name</b> to search.\n"
        "• Tap any result → goes to the channel post.\n"
        "• <b>Watch/Download</b> link auto-expires after set time.\n\n"
        "For admin commands, contact the bot owner.",
        parse_mode="HTML"
    )


# ── /stats ────────────────────────────────────────────────────────────────────

@router.message(Command("stats"))
async def cmd_stats(message: Message, **kwargs):
    s = await CosmicBotz.get_stats()
    await message.answer(
        "📊 <b>Bot Statistics</b>\n\n"
        f"📂 Total Index: <b>{s['total']}</b>\n"
        f"🎌 Anime: <b>{s['anime']}</b>\n"
        f"📺 TV Shows: <b>{s['tvshow']}</b>\n"
        f"🎬 Movies: <b>{s['movie']}</b>\n\n"
        f"📢 Channel Slots: <b>{s['slots']}</b>\n"
        f"🌐 Groups: <b>{s['groups']}</b> total, "
        f"<b>{s['verified_groups']}</b> verified",
        parse_mode="HTML"
    )
