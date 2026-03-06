from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, URLInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import CosmicBotz
from middlewares.auth import admin_only
from services.tmdb import search_tmdb, get_tv_details, get_movie_details, build_media_data
from services.caption import build_caption
from services.link_gen import create_and_save_link
from keyboards.inline import (
    tmdb_results_keyboard, media_type_keyboard,
    slot_list_keyboard, confirm_post_keyboard, watch_download_keyboard
)
import json

router = Router()


class AddContentState(StatesGroup):
    select_media_type = State()
    search_query      = State()
    select_result     = State()
    select_slot       = State()
    confirm_post      = State()


# ── /addcontent ───────────────────────────────────────────────────────────────

@router.message(Command("addcontent"))
@admin_only
async def cmd_addcontent(message: Message, state: FSMContext, **kwargs):
    await state.clear()
    await message.answer(
        "🎬 <b>Add New Content</b>\n\nSelect the media type:",
        reply_markup=media_type_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(AddContentState.select_media_type)


@router.callback_query(F.data.startswith("mtype_"), AddContentState.select_media_type)
async def cb_media_type(call: CallbackQuery, state: FSMContext):
    mtype = call.data.split("_")[1]
    label = {"anime": "Anime 🎌", "tvshow": "TV Show 📺", "movie": "Movie 🎬"}.get(mtype, mtype)
    await state.update_data(media_type=mtype)
    await call.message.edit_text(
        f"✅ Type: <b>{label}</b>\n\nSend the <b>title</b> to search on TMDB:",
        parse_mode="HTML"
    )
    await state.set_state(AddContentState.search_query)


@router.message(AddContentState.search_query)
async def got_search_query(message: Message, state: FSMContext):
    query = message.text.strip()
    data  = await state.get_data()
    mtype = data.get("media_type", "anime")
    tmdb_type = "movie" if mtype == "movie" else "tv"

    await message.answer(f"🔍 Searching TMDB for: <b>{query}</b>...", parse_mode="HTML")

    try:
        results = await search_tmdb(query, tmdb_type)
    except Exception as e:
        await message.answer(f"❌ TMDB search failed: {e}")
        await state.clear()
        return

    if not results:
        await message.answer("❌ No results found. Try a different title.")
        return

    await state.update_data(tmdb_results=json.dumps(results[:5]))
    await message.answer(
        f"📋 Found <b>{len(results[:5])}</b> results. Select the correct one:",
        reply_markup=tmdb_results_keyboard(results[:5], mtype),
        parse_mode="HTML"
    )
    await state.set_state(AddContentState.select_result)


@router.callback_query(F.data.startswith("tmdb_"), AddContentState.select_result)
async def cb_select_tmdb(call: CallbackQuery, state: FSMContext):
    parts   = call.data.split("_")
    mtype   = parts[1]
    tmdb_id = int(parts[2])

    await call.message.edit_text("⏳ Fetching full details from TMDB...")

    try:
        details    = await (get_movie_details(tmdb_id) if mtype == "movie" else get_tv_details(tmdb_id))
        media_data = build_media_data(details, mtype)
    except Exception as e:
        await call.message.edit_text(f"❌ Failed to fetch details: {e}")
        await state.clear()
        return

    filter_id = await CosmicBotz.add_filter(media_data.copy())
    if not filter_id:
        await call.message.edit_text("⚠️ This title already exists in the index!")
        await state.clear()
        return

    await state.update_data(media_data=json.dumps(media_data), filter_id=filter_id)

    # Preview caption
    caption = build_caption(media_data)
    caption += "\n\n🔗 <i>[Watch/Download button added after posting]</i>"
    poster  = media_data.get("poster_url")
    try:
        if poster:
            await call.message.answer_photo(URLInputFile(poster), caption=caption, parse_mode="HTML")
        else:
            await call.message.answer(caption, parse_mode="HTML")
    except Exception:
        await call.message.answer(caption, parse_mode="HTML")

    slots = await CosmicBotz.get_slots(call.from_user.id)
    if not slots:
        await call.message.answer("⚠️ No slots configured. Use /addslot first.")
        await state.clear()
        return

    await call.message.answer(
        "📢 Select the <b>channel slot</b> to post to:",
        reply_markup=slot_list_keyboard(slots),
        parse_mode="HTML"
    )
    await state.set_state(AddContentState.select_slot)


@router.callback_query(F.data.startswith("slot_"), AddContentState.select_slot)
async def cb_select_slot(call: CallbackQuery, state: FSMContext):
    channel_id = int(call.data.split("_")[1])
    data       = await state.get_data()
    filter_id  = data.get("filter_id")
    media_data = json.loads(data.get("media_data", "{}"))

    await state.update_data(selected_channel_id=channel_id)
    await call.message.edit_text(
        f"✅ Channel: <code>{channel_id}</code>\n"
        f"Title: <b>{media_data.get('title')}</b>\n\nReady to post?",
        reply_markup=confirm_post_keyboard(filter_id, channel_id),
        parse_mode="HTML"
    )
    await state.set_state(AddContentState.confirm_post)


@router.callback_query(F.data.startswith("post_"), AddContentState.confirm_post)
async def cb_confirm_post(call: CallbackQuery, state: FSMContext, bot: Bot):
    parts      = call.data.split("_")
    filter_id  = parts[1]
    channel_id = int(parts[2])
    data       = await state.get_data()
    media_data = json.loads(data.get("media_data", "{}"))
    await state.clear()

    settings       = await CosmicBotz.get_settings()
    revoke_minutes = settings.get("auto_revoke_minutes", 30)
    caption        = build_caption(media_data)
    poster         = media_data.get("poster_url")

    await call.message.edit_text("⏳ Posting to channel...")

    try:
        if poster:
            msg = await bot.send_photo(
                chat_id=channel_id,
                photo=URLInputFile(poster),
                caption=caption,
                parse_mode="HTML"
            )
        else:
            msg = await bot.send_message(chat_id=channel_id, text=caption, parse_mode="HTML")
    except Exception as e:
        await call.message.edit_text(f"❌ Failed to post: {e}")
        return

    try:
        invite_link, expires_at = await create_and_save_link(
            bot, channel_id, msg.message_id, revoke_minutes
        )
    except Exception as e:
        await call.message.edit_text(
            f"✅ Posted but couldn't create invite link: {e}\n"
            "Ensure bot has 'Invite Users via Link' permission."
        )
        return

    expires_str = expires_at.strftime("%H:%M UTC")
    try:
        await bot.edit_message_reply_markup(
            chat_id=channel_id,
            message_id=msg.message_id,
            reply_markup=watch_download_keyboard(invite_link, expires_str)
        )
    except Exception:
        pass

    await CosmicBotz.update_filter_post(filter_id, channel_id, msg.message_id)

    title = media_data.get("title", "?")
    await call.message.edit_text(
        f"✅ <b>{title}</b> posted!\n\n"
        f"🔗 Link expires: <b>{expires_str}</b> ({revoke_minutes} min)\n"
        f"📂 Indexed under letter: <b>{title[0].upper()}</b>",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "cancel_tmdb")
async def cb_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ Cancelled.")
