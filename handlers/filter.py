from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from database import CosmicBotz
from services.caption import build_index_caption
from keyboards.inline import index_results_keyboard

router  = Router()
ALPHABET = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")


@router.message(F.text)
async def handle_text(
    message: Message,
    is_group: bool = False,
    group_verified: bool = True,
    **kwargs
):
    if is_group and not group_verified:
        return

    text = (message.text or "").strip()
    if text.startswith("/"):
        return

    # Single letter → index
    if len(text) == 1 and text.upper() in ALPHABET:
        letter  = text.upper()
        results = await CosmicBotz.get_by_letter(letter)
        if not results:
            await message.answer(
                f"📂 <b>Index: '{letter}'</b>\n\nNo titles found for this letter.",
                parse_mode="HTML"
            )
            return
        await message.answer(
            build_index_caption(letter, results),
            reply_markup=index_results_keyboard(results),
            parse_mode="HTML"
        )
        return

    # Multi-char → search
    if len(text) >= 2:
        results = await CosmicBotz.search_title(text)
        if not results:
            await message.answer(
                f"🔍 No results found for: <b>{text}</b>",
                parse_mode="HTML"
            )
            return
        await message.answer(
            f"🔍 <b>Search: '{text}'</b>\nFound: <b>{len(results)}</b> result(s)",
            reply_markup=index_results_keyboard(results),
            parse_mode="HTML"
        )


@router.callback_query(F.data.startswith("nf_"))
async def cb_not_posted_yet(call: CallbackQuery):
    await call.answer("⚠️ This title hasn't been posted to the channel yet.", show_alert=True)
