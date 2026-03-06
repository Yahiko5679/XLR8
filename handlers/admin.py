from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ChatType

from database import CosmicBotz
from middlewares.auth import owner_only, admin_only, dm_only
from keyboards.inline import slot_list_keyboard, admin_list_keyboard

router = Router()


class AddSlotState(StatesGroup):
    waiting_channel_id = State()
    waiting_slot_name  = State()


# ── /addslot ──────────────────────────────────────────────────────────────────

@router.message(Command("addslot"))
@owner_only
@dm_only
async def cmd_addslot(message: Message, state: FSMContext, **kwargs):
    await message.answer(
        "➕ <b>Add New Slot</b>\n\n"
        "Forward any message from the <b>target channel</b>, "
        "or send its ID (e.g. <code>-100xxxxxxxxxx</code>).\n\n"
        "The bot must be an <b>admin</b> in that channel.",
        parse_mode="HTML"
    )
    await state.set_state(AddSlotState.waiting_channel_id)


@router.message(AddSlotState.waiting_channel_id)
async def slot_got_channel(message: Message, state: FSMContext):
    if message.forward_from_chat:
        channel_id   = message.forward_from_chat.id
        channel_name = message.forward_from_chat.title
    elif message.text and message.text.lstrip("-").isdigit():
        channel_id   = int(message.text.strip())
        channel_name = str(channel_id)
    else:
        await message.answer("⚠️ Send a valid channel ID or forward a message from the channel.")
        return

    await state.update_data(channel_id=channel_id, channel_name=channel_name)
    await message.answer(
        f"✅ Channel: <b>{channel_name}</b> (<code>{channel_id}</code>)\n\n"
        "Now send a <b>name/label</b> for this slot (e.g. <i>Anime Hindi Dub</i>):",
        parse_mode="HTML"
    )
    await state.set_state(AddSlotState.waiting_slot_name)


@router.message(AddSlotState.waiting_slot_name)
async def slot_got_name(message: Message, state: FSMContext):
    data         = await state.get_data()
    channel_id   = data["channel_id"]
    channel_name = data["channel_name"]
    slot_name    = message.text.strip()
    await state.clear()

    ok, msg = await CosmicBotz.add_slot(
        message.from_user.id, channel_id, channel_name, slot_name
    )
    if ok:
        await message.answer(
            f"✅ Slot <b>{slot_name}</b> added for <b>{channel_name}</b>!\n"
            "Use /addcontent to post content to this slot.",
            parse_mode="HTML"
        )
    else:
        await message.answer(f"⚠️ {msg}")


# ── /slots ────────────────────────────────────────────────────────────────────

@router.message(Command("slots"))
@owner_only
async def cmd_slots(message: Message, **kwargs):
    slots = await CosmicBotz.get_slots(message.from_user.id)
    if not slots:
        await message.answer("📭 No slots configured. Use /addslot to add one.")
        return
    await message.answer(
        f"📋 <b>Your Slots ({len(slots)})</b>",
        reply_markup=slot_list_keyboard(slots),
        parse_mode="HTML"
    )


# ── /removeslot ───────────────────────────────────────────────────────────────

@router.message(Command("removeslot"))
@owner_only
async def cmd_removeslot(message: Message, **kwargs):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: <code>/removeslot CHANNEL_ID</code>", parse_mode="HTML")
        return
    try:
        channel_id = int(args[1].strip())
    except ValueError:
        await message.answer("⚠️ Invalid channel ID.")
        return

    ok = await CosmicBotz.remove_slot(message.from_user.id, channel_id)
    if ok:
        await message.answer(f"✅ Slot removed for <code>{channel_id}</code>.", parse_mode="HTML")
    else:
        await message.answer("⚠️ Slot not found.")


# ── /addadmin / /removeadmin / /admins ────────────────────────────────────────

@router.message(Command("addadmin"))
@owner_only
async def cmd_addadmin(message: Message, **kwargs):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: <code>/addadmin USER_ID</code>", parse_mode="HTML")
        return
    try:
        user_id = int(args[1].strip())
    except ValueError:
        await message.answer("⚠️ Invalid user ID.")
        return
    await CosmicBotz.add_admin(user_id)
    await message.answer(f"✅ <code>{user_id}</code> added as admin.", parse_mode="HTML")


@router.message(Command("removeadmin"))
@owner_only
async def cmd_removeadmin(message: Message, **kwargs):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Usage: <code>/removeadmin USER_ID</code>", parse_mode="HTML")
        return
    try:
        user_id = int(args[1].strip())
    except ValueError:
        await message.answer("⚠️ Invalid user ID.")
        return
    await CosmicBotz.remove_admin(user_id)
    await message.answer(f"✅ <code>{user_id}</code> removed from admins.", parse_mode="HTML")


@router.message(Command("admins"))
@owner_only
async def cmd_list_admins(message: Message, **kwargs):
    admins = await CosmicBotz.get_admins()
    if not admins:
        await message.answer("👥 No admins set. Use /addadmin USER_ID.")
        return
    await message.answer(
        f"👥 <b>Admins ({len(admins)})</b>\nTap to remove:",
        reply_markup=admin_list_keyboard(admins),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("rmadmin_"))
async def cb_remove_admin(call: CallbackQuery):
    uid = int(call.data.split("_")[1])
    await CosmicBotz.remove_admin(uid)
    await call.answer(f"✅ Removed admin {uid}")
    await call.message.edit_text(f"✅ Admin <code>{uid}</code> removed.", parse_mode="HTML")


# ── /setrevoke ────────────────────────────────────────────────────────────────

@router.message(Command("setrevoke"))
@owner_only
async def cmd_setrevoke(message: Message, **kwargs):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        settings = await CosmicBotz.get_settings()
        current  = settings.get("auto_revoke_minutes", 30)
        await message.answer(
            f"⏱ Current auto-revoke: <b>{current} minutes</b>\n\n"
            "To change: <code>/setrevoke MINUTES</code>",
            parse_mode="HTML"
        )
        return
    try:
        minutes = int(args[1].strip())
        if minutes < 1:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Provide a valid number of minutes (min 1).")
        return
    await CosmicBotz.update_setting("auto_revoke_minutes", minutes)
    await message.answer(f"✅ Auto-revoke set to <b>{minutes} minutes</b>.", parse_mode="HTML")


# ── /settings ─────────────────────────────────────────────────────────────────

@router.message(Command("settings"))
@owner_only
async def cmd_settings(message: Message, **kwargs):
    settings = await CosmicBotz.get_settings()
    admins   = await CosmicBotz.get_admins()
    slots    = await CosmicBotz.get_slots(message.from_user.id)
    revoke   = settings.get("auto_revoke_minutes", 30)

    await message.answer(
        "⚙️ <b>Bot Settings</b>\n\n"
        f"🔗 Auto-Revoke: <b>{revoke} min</b> — /setrevoke\n"
        f"👥 Admins: <b>{len(admins)}</b> — /admins\n"
        f"📢 Slots: <b>{len(slots)}</b> — /slots\n\n"
        "/addslot · /addcontent · /addadmin · /groups",
        parse_mode="HTML"
    )
