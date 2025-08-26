
from __future__ import annotations

from datetime import datetime
from collections import defaultdict

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import settings
from app.db import get_session
from app.models import User
from app.services import create_support_ticket, redeem_access_code


bot = Bot(token=settings.user_bot_token)
dp = Dispatcher()

# Store last bot message id per user
user_last_bot_msg: dict[int, int] = {}


def main_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="Balance", callback_data="balance")
    kb.button(text="Withdraw", callback_data="withdraw")
    kb.button(text="Reinvest", callback_data="reinvest")
    kb.button(text="Support", callback_data="support")
    kb.button(text="Referral", callback_data="referral")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def reinvest_crypto_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🪙 SOL (Solana)", callback_data="reinvest_sol")
    kb.button(text="💎 USDT (TRC20)", callback_data="reinvest_usdt_trc20")
    kb.button(text="💎 USDT (ETH)", callback_data="reinvest_usdt_eth")
    kb.button(text="₿ BTC (Bitcoin)", callback_data="reinvest_btc")
    kb.button(text="🔙 Back to Menu", callback_data="back_to_menu")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


async def safe_delete_old_message(user_id: int, chat_id: int):
    msg_id = user_last_bot_msg.get(user_id)
    if msg_id:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
        except Exception:
            pass  # ignore errors if message already deleted or can't be deleted


async def send_clean_message(user_id: int, chat_id: int, text: str, reply_markup=None, parse_mode=None):
    await safe_delete_old_message(user_id, chat_id)
    msg = await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
    user_last_bot_msg[user_id] = msg.message_id


async def check_user_exists(callback: CallbackQuery) -> bool:
    with get_session() as session:
        user = session.get(User, callback.from_user.id)
        return user is not None


@dp.message(CommandStart())
async def start(message: Message):
    # Accept /start <code>
    args = (message.text or "").split(maxsplit=1)
    code = args[1].strip() if len(args) > 1 else ""
    if code:
        with get_session() as session:
            user = redeem_access_code(session, code=code, user_id=message.from_user.id)
            if user:
                await send_clean_message(message.from_user.id, message.chat.id, "✅ Access code redeemed. Your account is ready.", reply_markup=main_menu_kb())
                return
            else:
                await send_clean_message(message.from_user.id, message.chat.id, "❌ Invalid or expired code. If you think this is a mistake, contact support.", reply_markup=main_menu_kb())
    else:
        await send_clean_message(message.from_user.id, message.chat.id,
            "Welcome! Please provide your access code.\nYou can send it using /code <your_code>",
            reply_markup=main_menu_kb()
        )


@dp.message(Command("code"))
async def code_cmd(message: Message):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await send_clean_message(message.from_user.id, message.chat.id, "Usage: /code <your_access_code>", reply_markup=main_menu_kb())
        return
    code = parts[1].strip()
    with get_session() as session:
        user = redeem_access_code(session, code=code, user_id=message.from_user.id)
        if user:
            await send_clean_message(message.from_user.id, message.chat.id, "✅ Access code redeemed. Your account is ready.", reply_markup=main_menu_kb())
        else:
            await send_clean_message(message.from_user.id, message.chat.id, "❌ Invalid or expired code. Contact support.", reply_markup=main_menu_kb())


@dp.callback_query(F.data == "balance")
async def balance_cb(cb: CallbackQuery):
    if not await check_user_exists(cb):
        await send_clean_message(cb.from_user.id, cb.message.chat.id, "❌ Please redeem your access code first using /code <your_code>", reply_markup=main_menu_kb())
        await cb.answer()
        return
    with get_session() as session:
        user = session.get(User, cb.from_user.id)
        remaining_days = 0
        if user.next_roi_date:
            remaining_days = max(0, (user.next_roi_date.date() - cb.message.date.date()).days)
        text = (
            f"💼 Balance: {user.current_balance:.2f}\n"
            f"📈 ROI Cycle: {user.roi_cycles_completed} / 4\n"
            f"⏳ Next ROI in: {remaining_days} days"
        )
        await send_clean_message(cb.from_user.id, cb.message.chat.id, text, reply_markup=main_menu_kb())
    await cb.answer()


@dp.callback_query(F.data == "withdraw")
async def withdraw_cb(cb: CallbackQuery):
    if not await check_user_exists(cb):
        await send_clean_message(cb.from_user.id, cb.message.chat.id, "❌ Please redeem your access code first using /code <your_code>", reply_markup=main_menu_kb())
        await cb.answer()
        return
    with get_session() as session:
        user = session.get(User, cb.from_user.id)
        if not user.can_withdraw:
            await send_clean_message(
                cb.from_user.id,
                cb.message.chat.id,
                (
                    "🚫 You cannot withdraw yet!\n\n"
                    f"🕒 Your ROI cycles completed: {user.roi_cycles_completed} / 4\n"
                    "💡 You'll be able to withdraw after all 4 ROI cycles are complete."
                ),
                reply_markup=main_menu_kb()
            )
        else:
            await send_clean_message(cb.from_user.id, cb.message.chat.id, "📩 Withdrawal Request submitted to admin. Please wait for processing.", reply_markup=main_menu_kb())
            # Notify admin chat via user bot
            username = (cb.from_user.username or "").strip()
            mention = f"@{username}" if username else cb.from_user.full_name
            text = (
                "📩 Withdrawal Request!\n\n"
                f"👤 User: {mention} ({cb.from_user.id})\n"
                f"💼 Balance: {user.current_balance:.2f}\n"
                f"✅ ROI Completed: {user.roi_cycles_completed} / 4\n"
                "Please process the withdrawal manually."
            )
            if settings.admin_chat_id:
                await bot.send_message(chat_id=settings.admin_chat_id, text=text)
    await cb.answer()


@dp.callback_query(F.data == "reinvest")
async def reinvest_cb(cb: CallbackQuery):
    if not await check_user_exists(cb):
        await send_clean_message(cb.from_user.id, cb.message.chat.id, "❌ Please redeem your access code first using /code <your_code>", reply_markup=main_menu_kb())
        await cb.answer()
        return
    await safe_delete_old_message(cb.from_user.id, cb.message.chat.id)  # delete previous bot message
    msg = await bot.send_message(
        chat_id=cb.message.chat.id,
        text="📥 Choose your reinvestment cryptocurrency:",
        reply_markup=reinvest_crypto_kb()
    )
    user_last_bot_msg[cb.from_user.id] = msg.message_id
    await cb.answer()


@dp.callback_query(F.data == "reinvest_sol")
async def reinvest_sol_cb(cb: CallbackQuery):
    await send_clean_message(
        cb.from_user.id,
        cb.message.chat.id,
        (
            "🪙 **SOL (Solana) Reinvestment**\n\n"
            "Please send your SOL to the address below:\n\n"
            f"`{settings.sol_address}`\n\n"
            "⚠️ **Important:**\n"
            "• Only send SOL to this address\n"
            "• Double-check the address before sending\n"
            "• Once confirmed, an admin will credit your new balance"
        ),
        parse_mode="Markdown",
        reply_markup=main_menu_kb()
    )
    await cb.answer()


@dp.callback_query(F.data == "reinvest_usdt_trc20")
async def reinvest_usdt_trc20_cb(cb: CallbackQuery):
    await send_clean_message(
        cb.from_user.id,
        cb.message.chat.id,
        (
            "💎 **USDT (TRC20) Reinvestment**\n\n"
            "Please send your USDT via TRC20 network to:\n\n"
            f"`{settings.usdt_trc20_address}`\n\n"
            "⚠️ **Important:**\n"
            "• Only send USDT via TRC20 network\n"
            "• Network: TRON (TRC20)\n"
            "• Double-check the address before sending\n"
            "• Once confirmed, an admin will credit your new balance"
        ),
        parse_mode="Markdown",
        reply_markup=main_menu_kb()
    )
    await cb.answer()


@dp.callback_query(F.data == "reinvest_usdt_eth")
async def reinvest_usdt_eth_cb(cb: CallbackQuery):
    await send_clean_message(
        cb.from_user.id,
        cb.message.chat.id,
        (
            "💎 **USDT (Ethereum) Reinvestment**\n\n"
            "Please send your USDT via Ethereum network to:\n\n"
            f"`{settings.usdt_eth_address}`\n\n"
            "⚠️ **Important:**\n"
            "• Only send USDT via Ethereum network\n"
            "• Network: Ethereum (ERC20)\n"
            "• Double-check the address before sending\n"
            "• Once confirmed, an admin will credit your new balance"
        ),
        parse_mode="Markdown",
        reply_markup=main_menu_kb()
    )
    await cb.answer()


@dp.callback_query(F.data == "reinvest_btc")
async def reinvest_btc_cb(cb: CallbackQuery):
    await send_clean_message(
        cb.from_user.id,
        cb.message.chat.id,
        (
            "₿ **BTC (Bitcoin) Reinvestment**\n\n"
            "Please send your Bitcoin to the address below:\n\n"
            f"`{settings.btc_address}`\n\n"
            "⚠️ **Important:**\n"
            "• Only send BTC to this address\n"
            "• Double-check the address before sending\n"
            "• Once confirmed, an admin will credit your new balance"
        ),
        parse_mode="Markdown",
        reply_markup=main_menu_kb()
    )
    await cb.answer()


@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu_cb(cb: CallbackQuery):
    # Instead of just editing text, better delete old message & send new clean one with menu
    await send_clean_message(cb.from_user.id, cb.message.chat.id, "🔙 Back to main menu", reply_markup=main_menu_kb())
    await cb.answer()


@dp.callback_query(F.data == "support")
async def support_cb(cb: CallbackQuery):
    if not await check_user_exists(cb):
        await send_clean_message(cb.from_user.id, cb.message.chat.id, "❌ Please redeem your access code first using /code <your_code>", reply_markup=main_menu_kb())
        await cb.answer()
        return
    await send_clean_message(cb.from_user.id, cb.message.chat.id, "🛠 Support Request\n\nPlease describe your issue:", reply_markup=main_menu_kb())
    await cb.answer()


@dp.message(F.reply_to_message)
async def capture_support_reply(message: Message):
    # If the previous bot message contains the Support Request header, treat this as ticket
    if "Support Request" in (message.reply_to_message.text or ""):
        with get_session() as session:
            ticket = create_support_ticket(session, user_id=message.from_user.id, message=message.text or "")
        await send_clean_message(
            message.from_user.id,
            message.chat.id,
            f"🆘 New Support Ticket (#{ticket.ticket_id[:8]}) created and sent to admin.",
            reply_markup=main_menu_kb()
        )


@dp.callback_query(F.data == "referral")
async def referral_cb(cb: CallbackQuery):
    if not await check_user_exists(cb):
        await send_clean_message(cb.from_user.id, cb.message.chat.id, "❌ Please redeem your access code first using /code <your_code>", reply_markup=main_menu_kb())
        await cb.answer()
        return
    await send_clean_message(
        cb.from_user.id,
        cb.message.chat.id,
        "🚧 Referral System\n\n🔄 Stay tuned for updates!",
        reply_markup=main_menu_kb()
    )
    await cb.answer()


async def run_user_bot():
    await dp.start_polling(bot)
