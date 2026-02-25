from __future__ import annotations

import datetime as dt
from typing import Optional

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError

from app.config import ADMIN_IDS
from app.db import SessionLocal
from app.models import User, Invoice
from app.constants import PLANS
from app.utils import utcnow, in_30_days


router = Router()


# -------------------------
# UX: Keyboards
# -------------------------
def kb_admin_home() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="adm:stats")],
        [InlineKeyboardButton(text="🔎 User табуу", callback_data="adm:user_find")],
        [InlineKeyboardButton(text="🎁 Gift / Кредит кошуу", callback_data="adm:gift")],
        [InlineKeyboardButton(text="🧨 План коюу (FREE/PLUS/PRO)", callback_data="adm:setplan")],
        [InlineKeyboardButton(text="📣 Broadcast (баарына)", callback_data="adm:broadcast")],
        [InlineKeyboardButton(text="🚫 Ban / Unban", callback_data="adm:ban")],
        [InlineKeyboardButton(text="⬅️ Жабуу", callback_data="adm:close")],
    ])


def kb_admin_back() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Артка (Admin)", callback_data="adm:home")],
    ])


def kb_confirm(action: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ооба, аткар", callback_data=f"adm:confirm:{action}"),
            InlineKeyboardButton(text="❌ Жок, отмена", callback_data="adm:home"),
        ]
    ])


def kb_plan_choices() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🆓 FREE", callback_data="adm:plan:FREE"),
            InlineKeyboardButton(text="💎 PLUS", callback_data="adm:plan:PLUS"),
            InlineKeyboardButton(text="🔴 PRO", callback_data="adm:plan:PRO"),
        ],
        [InlineKeyboardButton(text="⬅️ Артка", callback_data="adm:home")],
    ])


def kb_gift_choices() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎥 VIP VIDEO +кредит", callback_data="adm:gift:video")],
        [InlineKeyboardButton(text="🪉 VIP MUSIC +минута", callback_data="adm:gift:music")],
        [InlineKeyboardButton(text="💬 CHAT +лимит", callback_data="adm:gift:chat")],
        [InlineKeyboardButton(text="⬅️ Артка", callback_data="adm:home")],
    ])


def kb_ban_choices() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚫 BAN кылуу", callback_data="adm:ban:on")],
        [InlineKeyboardButton(text="✅ UNBAN кылуу", callback_data="adm:ban:off")],
        [InlineKeyboardButton(text="⬅️ Артка", callback_data="adm:home")],
    ])


# -------------------------
# FSM (Admin input flows)
# -------------------------
class AdminFlow(StatesGroup):
    waiting_user_query = State()          # tg_id or @username
    waiting_plan_days = State()           # plan duration days
    waiting_gift_amount = State()         # amount of credits/minutes/chat
    waiting_broadcast_text = State()      # broadcast message text
    waiting_ban_reason = State()          # ban reason


# -------------------------
# Helpers
# -------------------------
def is_admin(tg_id: int) -> bool:
    return tg_id in set(ADMIN_IDS or [])


async def guard_admin(message_or_call) -> bool:
    uid = message_or_call.from_user.id
    if not is_admin(uid):
        # унчукпай коёбуз (security)
        try:
            if isinstance(message_or_call, Message):
                await message_or_call.answer("⛔ Админ эмессиң, досум 🙂")
            else:
                await message_or_call.answer("⛔", show_alert=True)
        except Exception:
            pass
        return False
    return True


def parse_user_query(q: str) -> tuple[Optional[int], Optional[str]]:
    q = (q or "").strip()
    if not q:
        return None, None
    if q.startswith("@"):
        return None, q[1:].lower()
    if q.isdigit():
        return int(q), None
    # username without @
    if " " not in q and len(q) >= 3:
        return None, q.lower()
    return None, None


async def get_user_by_query(q: str) -> Optional[User]:
    tg_id, uname = parse_user_query(q)
    async with SessionLocal() as s:
        if tg_id:
            res = await s.execute(select(User).where(User.tg_id == tg_id))
            return res.scalar_one_or_none()
        if uname:
            res = await s.execute(select(User).where(func.lower(User.username) == uname))
            return res.scalar_one_or_none()
    return None


def fmt_user(u: User) -> str:
    un = f"@{u.username}" if u.username else "(username жок)"
    plan_until = u.plan_until.isoformat() if u.plan_until else "-"
    blocked = u.blocked_until.isoformat() if getattr(u, "blocked_until", None) else "-"
    return (
        f"👤 User\n"
        f"• tg_id: {u.tg_id}\n"
        f"• username: {un}\n"
        f"• plan: {u.plan}\n"
        f"• plan_until: {plan_until}\n"
        f"• chat_left: {u.chat_left}\n"
        f"• vip_video_credits: {u.vip_video_credits}\n"
        f"• vip_music_minutes: {u.vip_music_minutes}\n"
        f"• blocked_until: {blocked}\n"
        f"• ref_balance_usd: {u.ref_balance_usd:.2f}\n"
    )


# -------------------------
# Entry: /admin
# -------------------------
@router.message(F.text == "/admin")
async def admin_entry(m: Message, state: FSMContext):
    if not await guard_admin(m):
        return
    await state.clear()
    await m.answer("🧠 *ADMIN PANEL*\nТанда, досум 😈💎", reply_markup=kb_admin_home())


@router.callback_query(F.data == "adm:home")
async def admin_home(c: CallbackQuery, state: FSMContext):
    if not await guard_admin(c):
        return
    await state.clear()
    await c.message.edit_text("🧠 *ADMIN PANEL*\nТанда, досум 😈💎", reply_markup=kb_admin_home())
    await c.answer()


@router.callback_query(F.data == "adm:close")
async def admin_close(c: CallbackQuery, state: FSMContext):
    if not await guard_admin(c):
        return
    await state.clear()
    await c.message.edit_text("✅ Жабылды. /admin десең кайра ачылат 😎")
    await c.answer()


# -------------------------
# Stats
# -------------------------
@router.callback_query(F.data == "adm:stats")
async def admin_stats(c: CallbackQuery):
    if not await guard_admin(c):
        return

    async with SessionLocal() as s:
        total_users = (await s.execute(select(func.count(User.id)))).scalar_one()
        plan_free = (await s.execute(select(func.count(User.id)).where(User.plan == "FREE"))).scalar_one()
        plan_plus = (await s.execute(select(func.count(User.id)).where(User.plan == "PLUS"))).scalar_one()
        plan_pro = (await s.execute(select(func.count(User.id)).where(User.plan == "PRO"))).scalar_one()

        paid_cnt = (await s.execute(select(func.count(Invoice.id)).where(Invoice.status == "paid"))).scalar_one()
        revenue = (await s.execute(select(func.coalesce(func.sum(Invoice.amount_usd), 0.0)).where(Invoice.status == "paid"))).scalar_one()

    text = (
        "📊 *Stats*\n\n"
        f"👥 Users: {total_users}\n"
        f"🆓 FREE: {plan_free}\n"
        f"💎 PLUS: {plan_plus}\n"
        f"🔴 PRO: {plan_pro}\n\n"
        f"✅ Paid invoices: {paid_cnt}\n"
        f"💰 Revenue (USD): {float(revenue):.2f}\n\n"
        "😈 Досум, бул сандар өссө — сен масштабга чыктың деген сөз!"
    )

    await c.message.edit_text(text, reply_markup=kb_admin_back())
    await c.answer)


# -------------------------
# User Find
# -------------------------
@router.callback_query(F.data == "adm:user_find")
async def admin_user_find(c: CallbackQuery, state: FSMContext):
    if not await guard_admin(c):
        return
    await state.clear()
    await state.set_state(AdminFlow.waiting_user_query)
    await c.message.edit_text(
        "🔎 *User табуу*\n\n"
        "Жаз:\n"
        "• tg_id (мисал: 123456789)\n"
        "же\n"
        "• @username (мисал: @tilek)\n",
        reply_markup=kb_admin_back()
    )
    await c.answer()


@router.message(AdminFlow.waiting_user_query)
async def admin_user_find_input(m: Message, state: FSMContext):
    if not await guard_admin(m):
        return

    u = await get_user_by_query(m.text)
    if not u:
        await m.answer("❌ Табылган жок, досум 😅\nКайра жаз: tg_id же @username", reply_markup=kb_admin_back())
        return

    await state.update_data(last_user_tg_id=u.tg_id)
    await m.answer(fmt_user(u), reply_markup=kb_admin_back())


# -------------------------
# Gift (credits)
# -------------------------
@router.callback_query(F.data == "adm:gift")
async def admin_gift_menu(c: CallbackQuery, state: FSMContext):
    if not await guard_admin(c):
        return
    await state.clear()
    await c.message.edit_text("🎁 *Gift меню*\nЭмнени кошобуз?", reply_markup=kb_gift_choices())
    await c.answer()


@router.callback_query(F.data.startswith("adm:gift:"))
async def admin_gift_pick(c: CallbackQuery, state: FSMContext):
    if not await guard_admin(c):
        return
    kind = c.data.split(":")[-1]  # video/music/chat

    await state.clear()
    await state.set_state(AdminFlow.waiting_user_query)
    await state.update_data(gift_kind=kind)

    title = {"video": "🎥 VIP VIDEO", "music": "🪉 VIP MUSIC", "chat": "💬 CHAT"}[kind]
    await c.message.edit_text(
        f"{title} кошобуз.\n\n"
        "Алгач user жаз:\n"
        "• tg_id же • @username",
        reply_markup=kb_admin_back()
    )
    await c.answer()


@router.message(AdminFlow.waiting_user_query)
async def admin_waiting_user_then_amount(m: Message, state: FSMContext):
    """
    Бул handler user_find’ден кийин да түшүшү мүмкүн.
    Ошондуктан data ичинде gift_kind бар болсо — gift flow,
    болбосо user_find flow иштей берет.
    """
    if not await guard_admin(m):
        return

    data = await state.get_data()
    gift_kind = data.get("gift_kind")

    # Эгер gift эмес болсо — user_find flow мурдагы функцияда кармалат.
    if not gift_kind:
        # user find иштетип коёбуз
        u = await get_user_by_query(m.text)
        if not u:
            await m.answer("❌ Табылган жок, кайра жаз: tg_id же @username", reply_markup=kb_admin_back())
            return
        await state.update_data(last_user_tg_id=u.tg_id)
        await m.answer(fmt_user(u), reply_markup=kb_admin_back())
        return

    # Gift flow
    u = await get_user_by_query(m.text)
    if not u:
        await m.answer("❌ Табылган жок 😅\nКайра жаз: tg_id же @username", reply_markup=kb_admin_back())
        return

    await state.update_data(last_user_tg_id=u.tg_id)
    await state.set_state(AdminFlow.waiting_gift_amount)

    hint = "сан жаз (мисал: 3)"
    if gift_kind == "music":
        hint = "минут сан жаз (мисал: 5)"
    await m.answer(f"✅ Таптым:\n{fmt_user(u)}\nЭми кошула турган {hint}:", reply_markup=kb_admin_back())


@router.message(AdminFlow.waiting_gift_amount)
async def admin_gift_apply(m: Message, state: FSMContext):
    if not await guard_admin(m):
        return

    data = await state.get_data()
    gift_kind = data.get("gift_kind")
    target_tg_id = data.get("last_user_tg_id")

    if not gift_kind or not target_tg_id:
        await state.clear()
        await m.answer("⚠️ Flow бузулду. /admin кайра ач 😅")
        return

    if not (m.text or "").strip().isdigit():
        await m.answer("❌ Сан жаз, досум 😈 (мисал: 3)")
        return

    amount = int(m.text.strip())
    if amount <= 0 or amount > 100000:
        await m.answer("❌ Туура сан бер: 1..100000")
        return
    async with SessionLocal() as s:
        res = await s.execute(select(User).where(User.tg_id == target_tg_id))
        u = res.scalar_one_or_none()
        if not u:
            await m.answer("❌ User DBде жок болуп калды 😅")
            return

        if gift_kind == "video":
            u.vip_video_credits += amount
            done = f"🎥 VIP VIDEO кредит: +{amount}"
        elif gift_kind == "music":
            u.vip_music_minutes += amount
            done = f"🪉 VIP MUSIC минут: +{amount}"
        else:
            u.chat_left += amount
            done = f"💬 CHAT лимит: +{amount}"

        await s.commit()

    await state.clear()
    await m.answer(f"✅ Done!\n{done}\n\nTarget: {target_tg_id}", reply_markup=kb_admin_home())


# -------------------------
# Set Plan
# -------------------------
@router.callback_query(F.data == "adm:setplan")
async def admin_setplan_menu(c: CallbackQuery, state: FSMContext):
    if not await guard_admin(c):
        return
    await state.clear()
    await c.message.edit_text("🧨 *План коюу*\nАлгач план танда:", reply_markup=kb_plan_choices())
    await c.answer()


@router.callback_query(F.data.startswith("adm:plan:"))
async def admin_setplan_pick(c: CallbackQuery, state: FSMContext):
    if not await guard_admin(c):
        return

    plan = c.data.split(":")[-1]  # FREE/PLUS/PRO
    if plan not in ("FREE", "PLUS", "PRO"):
        await c.answer("Ката", show_alert=True)
        return

    await state.clear()
    await state.update_data(target_plan=plan)
    await state.set_state(AdminFlow.waiting_user_query)

    await c.message.edit_text(
        f"✅ План: *{plan}*\n\n"
        "Эми user жаз:\n"
        "• tg_id же • @username",
        reply_markup=kb_admin_back()
    )
    await c.answer()


@router.message(AdminFlow.waiting_plan_days)
async def admin_setplan_days(m: Message, state: FSMContext):
    if not await guard_admin(m):
        return

    data = await state.get_data()
    plan = data.get("target_plan")
    target_tg_id = data.get("last_user_tg_id")

    if not plan or not target_tg_id:
        await state.clear()
        await m.answer("⚠️ Flow бузулду. /admin кайра ач 😅")
        return

    if not (m.text or "").strip().isdigit():
        await m.answer("❌ Күн сан жаз (мисал: 30)")
        return

    days = int(m.text.strip())
    if days <= 0 or days > 3650:
        await m.answer("❌ Күн 1..3650 болсун 😈")
        return

    async with SessionLocal() as s:
        res = await s.execute(select(User).where(User.tg_id == target_tg_id))
        u = res.scalar_one_or_none()
        if not u:
            await m.answer("❌ User табылган жок 😅")
            return

        u.plan = plan
        if plan == "FREE":
            u.plan_until = None
        else:
            u.plan_until = utcnow() + dt.timedelta(days=days)
            # refill limits immediately
            p = PLANS[plan]
            u.chat_left = p.monthly_chat
            u.video_left = p.monthly_video
            u.music_left = p.monthly_music
            u.image_left = p.monthly_image
            u.voice_left = p.monthly_voice
            u.doc_left = p.monthly_doc
            u.last_monthly_reset = utcnow()

        await s.commit()

    await state.clear()
    await m.answer(f"✅ План коюлду: {plan} ({days} күн)\nTarget: {target_tg_id}", reply_markup=kb_admin_home())


# Hook user selection for setplan
@router.message(AdminFlow.waiting_user_query)
async def admin_setplan_user_then_days(m: Message, state: FSMContext):
    if not await guard_admin(m):
        return

    data = await state.get_data()
    plan = data.get("target_plan")
    gift_kind = data.get("gift_kind")

    # setplan flow (эгер target_plan бар болсо)
    if plan and not gift_kind:
        u = await get_user_by_query(m.text)
        if not u:
            await m.answer("❌ Табылган жок, кайра жаз: tg_id же @username", reply_markup=kb_admin_back())
            return
        await state.update_data(last_user_tg_id=u.tg_id)
        if plan == "FREE":
            # FREE үчүн күн сурабай эле коюп салабыз
            async with SessionLocal() as s:
                res = await s.execute(select(User).where(User.tg_id == u.tg_id))
                uu = res.scalar_one()
                uu.plan = "FREE"
                uu.plan_until = None
                await s.commit()
            await state.clear()
            await m.answer(f"✅ План коюлду: FREE\nTarget: {u.tg_id}", reply_markup=kb_admin_home())
            return

        await state.set_state(AdminFlow.waiting_plan_days)
        await m.answer(f"✅ Таптым:\n{fmt_user(u)}\nЭми канча күн? (мисал: 30)", reply_markup=kb_admin_back())
        return

    # калган учурлар: башка flow handler’лер кармайт
    # бул жерде эч нерсе кылбайбыз


# -------------------------
# Broadcast
# -------------------------
@router.callback_query(F.data == "adm:broadcast")
async def admin_broadcast_start(c: CallbackQuery, state: FSMContext):
    if not await guard_admin(c):
        return
    await state.clear()
    await state.set_state(AdminFlow.waiting_broadcast_text)
    await c.message.edit_text(
        "📣 *Broadcast*\n\n"
        "Эми баарына жибере турган текстти жаз.\n"
        "⚠️ Этият бол: бул бардык user’ге кетет.",
        reply_markup=kb_admin_back()
    )
    await c.answer()


@router.message(AdminFlow.waiting_broadcast_text)
async def admin_broadcast_confirm(m: Message, state: FSMContext):
    if not await guard_admin(m):
        return
    text = (m.text or "").strip()
    if len(text) < 3:
        await m.answer("❌ Текст өтө кыска 😅")
        return

    await state.update_data(broadcast_text=text)
    await m.answer(
        "😈 Досум, confirm кылайлы!\n\n"
        f"Текст:\n{text}\n\n"
        "Жөнөтөбүзбү?",
        reply_markup=kb_confirm("broadcast")
    )


@router.callback_query(F.data == "adm:confirm:broadcast")
async def admin_broadcast_send(c: CallbackQuery, state: FSMContext):
    if not await guard_admin(c):
        return
    data = await state.get_data()
    text = data.get("broadcast_text")
    if not text:
        await state.clear()
        await c.message.edit_text("⚠️ Текст табылган жок. /admin кайра ач 😅", reply_markup=kb_admin_home())
        await c.answer()
        return

    # collect users
    async with SessionLocal() as s:
        ids = (await s.execute(select(User.tg_id))).scalars().all()

    ok, fail = 0, 0
    for tg_id in ids:
        try:
            await c.bot.send_message(tg_id, text)
            ok += 1
        except Exception:
            fail += 1

    await state.clear()
    await c.message.edit_text(
        f"✅ Broadcast бүттү!\n"
        f"📨 Sent: {ok}\n"
        f"⚠️ Failed: {fail}\n",
        reply_markup=kb_admin_home()
    )
    await c.answer()


# -------------------------
# Ban / Unban
# -------------------------
@router.callback_query(F.data == "adm:ban")
async def admin_ban_menu(c: CallbackQuery, state: FSMContext):
    if not await guard_admin(c):
        return
    await state.clear()
    await c.message.edit_text("🚫 *Ban меню*\nТанда:", reply_markup=kb_ban_choices())
    await c.answer()


@router.callback_query(F.data.startswith("adm:ban:"))
async def admin_ban_pick(c: CallbackQuery, state: FSMContext):
    if not await guard_admin(c):
        return
    mode = c.data.split(":")[-1]  # on/off
    if mode not in ("on", "off"):
        await c.answer("Ката", show_alert=True)
        return

    await state.clear()
    await state.update_data(ban_mode=mode)
    await state.set_state(AdminFlow.waiting_user_query)

    await c.message.edit_text(
        f"🚫Mode: *{mode.upper()}*\n\nUser жаз: tg_id же @username",
        reply_markup=kb_admin_back()
    )
    await c.answer()


@router.message(AdminFlow.waiting_ban_reason)
async def admin_ban_apply(m: Message, state: FSMContext):
    if not await guard_admin(m):
        return

    data = await state.get_data()
    target_tg_id = data.get("last_user_tg_id")
    mode = data.get("ban_mode")

    reason = (m.text or "").strip()
    if not reason:
        reason = "Admin decision"

    async with SessionLocal() as s:
        res = await s.execute(select(User).where(User.tg_id == target_tg_id))
        u = res.scalar_one_or_none()
        if not u:
            await m.answer("❌ User табылган жок 😅")
            return

        # Бул field’дер models.py’да болушу керек.
        setattr(u, "is_banned", True if mode == "on" else False)
        setattr(u, "banned_reason", reason if mode == "on" else None)
        await s.commit()

    await state.clear()
    await m.answer(f"✅ {mode.upper()} done\nTarget: {target_tg_id}\nReason: {reason}", reply_markup=kb_admin_home())


@router.message(AdminFlow.waiting_user_query)
async def admin_ban_user_then_reason(m: Message, state: FSMContext):
    """
    Ban flow: user -> (if ban on) reason -> apply
    """
    if not await guard_admin(m):
        return

    data = await state.get_data()
    mode = data.get("ban_mode")
    plan = data.get("target_plan")
    gift_kind = data.get("gift_kind")

    # Эгер ban_mode жок болсо — бул handler башка flow’го тиешелүү, унчукпайбыз.
    if not mode or plan or gift_kind:
        return

    u = await get_user_by_query(m.text)
    if not u:
        await m.answer("❌ Табылган жок, кайра жаз: tg_id же @username", reply_markup=kb_admin_back())
        return

    await state.update_data(last_user_tg_id=u.tg_id)

    if mode == "off":
        # Unban үчүн reason сурабай эле койсок болот
        async with SessionLocal() as s:
            res = await s.execute(select(User).where(User.tg_id == u.tg_id))
            uu = res.scalar_one()
            setattr(uu, "is_banned", False)
            setattr(uu, "banned_reason", None)
            await s.commit()

        await state.clear()
        await m.answer(f"✅ UNBAN done\nTarget: {u.tg_id}", reply_markup=kb_admin_home())
        return

    # Ban on => reason сурайбыз
    await state.set_state(AdminFlow.waiting_ban_reason)
    await m.answer(f"✅ Таптым:\n{fmt_user(u)}\n\nЭми BAN reason жаз (кыскача):", reply_markup=kb_admin_back())


