
from __future__ import annotations

from datetime import datetime
from collections import defaultdict

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.config import settings
from app.db import get_session
from app.models import User
from app.services import create_support_ticket, redeem_access_code


bot = Bot(token=settings.user_bot_token)
dp = Dispatcher()

# Store last bot message id per user
user_last_bot_msg: dict[int, int] = {}


class SupportStates(StatesGroup):
    waiting_for_message = State()


def main_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Balance", callback_data="balance")
    kb.button(text="📈 Earnings Calculator", callback_data="earnings_calculator")
    kb.button(text="📊 Investment History", callback_data="investment_history")
    kb.button(text="💸 Withdraw", callback_data="withdraw")
    kb.button(text="🔄 Reinvest", callback_data="reinvest")
    kb.button(text="🎫 Support", callback_data="support")
    kb.button(text="👥 Referral", callback_data="referral")
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup()


def support_menu_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📝 Create Support Ticket", callback_data="create_ticket")
    kb.button(text="🔙 Back to Main Menu", callback_data="back_to_main")
    kb.adjust(1, 1)
    return kb.as_markup()


def cancel_support_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="❌ Cancel", callback_data="cancel_support")
    kb.adjust(1)
    return kb.as_markup()


def back_to_main_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🔙 Back to Main Menu", callback_data="back_to_main")
    kb.adjust(1)
    return kb.as_markup()


def earnings_calculator_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📊 View Projections", callback_data="view_projections")
    kb.button(text="📈 Weekly Breakdown", callback_data="weekly_breakdown")
    kb.button(text="🔙 Back to Main Menu", callback_data="back_to_main")
    kb.adjust(1, 1, 1)
    return kb.as_markup()


def investment_history_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📋 All Transactions", callback_data="all_transactions")
    kb.button(text="💰 ROI Payments", callback_data="roi_transactions")
    kb.button(text="🔄 Reinvestments", callback_data="reinvestment_transactions")
    kb.button(text="🔙 Back to Main Menu", callback_data="back_to_main")
    kb.adjust(1, 1, 1, 1)
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
            "Please send your USDT via TRON network to:\n\n"
            f"`{settings.usdt_trc20_address}`\n\n"
            "⚠️ **Important:**\n"
            "• Only send USDT via TRON network\n"
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
    
    await send_clean_message(
        cb.from_user.id, 
        cb.message.chat.id, 
        "🛠 **Support Center**\n\n"
        "How can we help you today?",
        reply_markup=support_menu_kb(),
        parse_mode="Markdown"
    )
    await cb.answer()


@dp.callback_query(F.data == "create_ticket")
async def create_ticket_cb(cb: CallbackQuery, state: FSMContext):
    await state.set_state(SupportStates.waiting_for_message)
    await send_clean_message(
        cb.from_user.id,
        cb.message.chat.id,
        "📝 **Create Support Ticket**\n\n"
        "Please describe your issue or question in detail.\n\n"
        "💡 **Tips:**\n"
        "• Be specific about your problem\n"
        "• Include any error messages\n"
        "• Mention your user ID if relevant\n\n"
        "Type your message below:",
        reply_markup=cancel_support_kb(),
        parse_mode="Markdown"
    )
    await cb.answer()


@dp.callback_query(F.data == "cancel_support")
async def cancel_support_cb(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await send_clean_message(
        cb.from_user.id,
        cb.message.chat.id,
        "❌ Support ticket creation cancelled.",
        reply_markup=main_menu_kb()
    )
    await cb.answer()


@dp.message(StateFilter(SupportStates.waiting_for_message))
async def handle_support_message(message: Message, state: FSMContext):
    # Validate message
    if not message.text or len(message.text.strip()) < 10:
        await send_clean_message(
            message.from_user.id,
            message.chat.id,
            "❌ **Message too short!**\n\n"
            "Please provide a detailed description (at least 10 characters).\n"
            "Try again with more details:",
            reply_markup=cancel_support_kb(),
            parse_mode="Markdown"
        )
        return
    
    # Create support ticket
    try:
        with get_session() as session:
            ticket = create_support_ticket(
                session, 
                user_id=message.from_user.id, 
                message=message.text.strip()
            )
        
        # Clear state
        await state.clear()
        
        # Send confirmation
        await send_clean_message(
            message.from_user.id,
            message.chat.id,
            f"✅ **Support Ticket Created!**\n\n"
            f"🎫 **Ticket ID:** `{ticket.ticket_id[:8]}`\n"
            f"📝 **Your Message:** {message.text.strip()[:100]}{'...' if len(message.text) > 100 else ''}\n\n"
            f"📧 An admin will review your ticket and respond soon.\n"
            f"⏰ **Created:** {ticket.created_at.strftime('%Y-%m-%d %H:%M UTC')}",
            reply_markup=main_menu_kb(),
            parse_mode="Markdown"
        )
        
        # Notify admin
        if settings.admin_chat_id:
            username = (message.from_user.username or "").strip()
            mention = f"@{username}" if username else message.from_user.full_name
            
            admin_notification = (
                f"🆘 **New Support Ticket**\n\n"
                f"👤 **User:** {mention} (ID: {message.from_user.id})\n"
                f"🎫 **Ticket:** `{ticket.ticket_id[:8]}`\n"
                f"📝 **Message:** {message.text.strip()}\n"
                f"⏰ **Time:** {ticket.created_at.strftime('%Y-%m-%d %H:%M UTC')}"
            )
            
            await bot.send_message(
                chat_id=settings.admin_chat_id,
                text=admin_notification,
                parse_mode="Markdown"
            )
            
    except Exception as e:
        await send_clean_message(
            message.from_user.id,
            message.chat.id,
            f"❌ **Error creating ticket!**\n\n"
            f"Please try again later or contact admin directly.\n"
            f"Error: {str(e)}",
            reply_markup=main_menu_kb(),
            parse_mode="Markdown"
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


# Add missing callback handlers
@dp.callback_query(F.data == "earnings_calculator")
async def earnings_calculator_cb(callback: CallbackQuery):
    """Show earnings calculator menu"""
    if not await check_user_exists(callback):
        await send_clean_message(callback.from_user.id, callback.message.chat.id, "❌ Please redeem your access code first using /code <your_code>", reply_markup=main_menu_kb())
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "📈 **Earnings Calculator**\n\n"
        "Calculate your projected earnings and ROI growth potential:",
        reply_markup=earnings_calculator_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data == "view_projections")
async def view_projections_cb(callback: CallbackQuery):
    """Show earnings projections"""
    try:
        with get_session() as session:
            user = session.get(User, callback.from_user.id)
            if not user:
                await callback.message.edit_text(
                    "❌ **User not found!**\n\n"
                    "Please contact an administrator to register your account.",
                    reply_markup=back_to_main_kb(),
                    parse_mode="Markdown"
                )
                await callback.answer()
                return
            
            # Calculate projections manually since we don't have the service functions
            remaining_cycles = user.max_roi_cycles - user.roi_cycles_completed
            weekly_roi_percent = 8.0  # From settings
            
            if remaining_cycles <= 0:
                projection_text = (
                    "🎯 **Investment Complete!**\n\n"
                    f"✅ You have completed all {user.max_roi_cycles} ROI cycles\n"
                    f"💰 Final Balance: **${user.current_balance:.2f}**\n"
                    f"🚪 Withdrawal: **{'Enabled' if user.can_withdraw else 'Disabled'}**\n\n"
                    "🎉 Congratulations on completing your investment journey!"
                )
            else:
                weekly_roi_decimal = weekly_roi_percent / 100.0
                total_projected = user.current_balance
                roi_earnings = 0.0
                
                for week in range(1, remaining_cycles + 1):
                    weekly_roi = user.current_balance * weekly_roi_decimal
                    roi_earnings += weekly_roi
                    total_projected += weekly_roi
                
                from datetime import timedelta
                completion_date = datetime.utcnow() + timedelta(days=remaining_cycles * 7)
                
                projection_text = (
                    "📊 **Earnings Projection**\n\n"
                    f"💰 **Current Balance:** ${user.current_balance:.2f}\n"
                    f"📈 **ROI Cycles:** {user.roi_cycles_completed}/{user.max_roi_cycles}\n"
                    f"⏳ **Remaining Cycles:** {remaining_cycles}\n"
                    f"🎯 **Weekly ROI:** {weekly_roi_percent}%\n\n"
                    f"🚀 **Projected Final Balance:** ${total_projected:.2f}\n"
                    f"💵 **Total ROI Earnings:** ${roi_earnings:.2f}\n"
                    f"📅 **Completion Date:** {completion_date.strftime('%Y-%m-%d')}"
                )
            
            await callback.message.edit_text(
                projection_text,
                reply_markup=earnings_calculator_kb(),
                parse_mode="Markdown"
            )
            
    except Exception as e:
        await callback.message.edit_text(
            f"❌ **Error calculating projections:** {str(e)}",
            reply_markup=earnings_calculator_kb(),
            parse_mode="Markdown"
        )
    
    await callback.answer()


@dp.callback_query(F.data == "weekly_breakdown")
async def weekly_breakdown_cb(callback: CallbackQuery):
    """Show weekly ROI breakdown"""
    try:
        with get_session() as session:
            user = session.get(User, callback.from_user.id)
            if not user:
                await callback.message.edit_text(
                    "❌ **User not found!**\n\n"
                    "Please contact an administrator to register your account.",
                    reply_markup=earnings_calculator_kb(),
                    parse_mode="Markdown"
                )
                await callback.answer()
                return
            
            remaining_cycles = user.max_roi_cycles - user.roi_cycles_completed
            weekly_roi_percent = 8.0
            
            if remaining_cycles <= 0:
                breakdown_text = "✅ **No remaining ROI cycles to project.**"
            else:
                breakdown_text = "📅 **Weekly ROI Breakdown**\n\n"
                weekly_roi_decimal = weekly_roi_percent / 100.0
                total_projected = user.current_balance
                roi_earnings = 0.0
                
                for week in range(1, remaining_cycles + 1):
                    weekly_roi = user.current_balance * weekly_roi_decimal
                    roi_earnings += weekly_roi
                    total_projected += weekly_roi
                    
                    breakdown_text += (
                        f"**Week {week}:**\n"
                        f"   💰 ROI: +${weekly_roi:.2f}\n"
                        f"   📊 Cumulative: ${roi_earnings:.2f}\n"
                        f"   💵 Balance: ${total_projected:.2f}\n\n"
                    )
            
            await callback.message.edit_text(
                breakdown_text,
                reply_markup=earnings_calculator_kb(),
                parse_mode="Markdown"
            )
            
    except Exception as e:
        await callback.message.edit_text(
            f"❌ **Error showing breakdown:** {str(e)}",
            reply_markup=earnings_calculator_kb(),
            parse_mode="Markdown"
        )
    
    await callback.answer()


@dp.callback_query(F.data == "investment_history")
async def investment_history_cb(callback: CallbackQuery):
    """Show investment history menu"""
    if not await check_user_exists(callback):
        await send_clean_message(callback.from_user.id, callback.message.chat.id, "❌ Please redeem your access code first using /code <your_code>", reply_markup=main_menu_kb())
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "📊 **Investment History**\n\n"
        "Track all your financial transactions and investment activity:",
        reply_markup=investment_history_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data == "all_transactions")
async def all_transactions_cb(callback: CallbackQuery):
    """Show all transactions"""
    try:
        with get_session() as session:
            user = session.get(User, callback.from_user.id)
            if not user:
                await callback.message.edit_text(
                    "❌ **User not found!**\n\n"
                    "Please contact an administrator to register your account.",
                    reply_markup=investment_history_kb(),
                    parse_mode="Markdown"
                )
                await callback.answer()
                return
            
            # For now, show basic user info since we don't have the full transaction system
            transaction_text = (
                "📋 **Your Investment Summary**\n\n"
                f"💰 **Current Balance:** ${user.current_balance:.2f}\n"
                f"💳 **Initial Investment:** ${user.initial_balance:.2f}\n"
                f"📈 **ROI Cycles Completed:** {user.roi_cycles_completed}/{user.max_roi_cycles}\n"
                f"💵 **Total ROI Earned:** ${user.current_balance - user.initial_balance:.2f}\n"
                f"📅 **Account Created:** {user.created_at.strftime('%Y-%m-%d')}\n\n"
                "💡 **Note:** Detailed transaction history will be available in the next update!"
            )
            
            await callback.message.edit_text(
                transaction_text,
                reply_markup=investment_history_kb(),
                parse_mode="Markdown"
            )
            
    except Exception as e:
        await callback.message.edit_text(
            f"❌ **Error loading transactions:** {str(e)}",
            reply_markup=investment_history_kb(),
            parse_mode="Markdown"
        )
    
    await callback.answer()


@dp.callback_query(F.data == "roi_transactions")
async def roi_transactions_cb(callback: CallbackQuery):
    """Show ROI payment transactions"""
    try:
        with get_session() as session:
            user = session.get(User, callback.from_user.id)
            if not user:
                await callback.message.edit_text(
                    "❌ **User not found!**\n\n"
                    "Please contact an administrator to register your account.",
                    reply_markup=investment_history_kb(),
                    parse_mode="Markdown"
                )
                await callback.answer()
                return
            
            if user.roi_cycles_completed == 0:
                roi_text = "💰 **No ROI Payments Yet**\n\nROI payments will appear here once they start processing."
            else:
                total_roi = user.current_balance - user.initial_balance
                roi_text = (
                    f"💰 **ROI Payment Summary**\n\n"
                    f"📈 **ROI Cycles Completed:** {user.roi_cycles_completed}\n"
                    f"💵 **Total ROI Received:** ${total_roi:.2f}\n"
                    f"🎯 **Weekly ROI Rate:** 8%\n\n"
                    "💡 **Note:** Detailed weekly breakdown will be available in the next update!"
                )
            
            await callback.message.edit_text(
                roi_text,
                reply_markup=investment_history_kb(),
                parse_mode="Markdown"
            )
            
    except Exception as e:
        await callback.message.edit_text(
            f"❌ **Error loading ROI transactions:** {str(e)}",
            reply_markup=investment_history_kb(),
            parse_mode="Markdown"
        )
    
    await callback.answer()


@dp.callback_query(F.data == "reinvestment_transactions")
async def reinvestment_transactions_cb(callback: CallbackQuery):
    """Show reinvestment transactions"""
    try:
        with get_session() as session:
            user = session.get(User, callback.from_user.id)
            if not user:
                await callback.message.edit_text(
                    "❌ **User not found!**\n\n"
                    "Please contact an administrator to register your account.",
                    reply_markup=investment_history_kb(),
                    parse_mode="Markdown"
                )
                await callback.answer()
                return
            
            reinvest_text = (
                "🔄 **Reinvestment Status**\n\n"
                "💡 **Current Status:** No active reinvestments\n\n"
                "🚀 **How to Reinvest:**\n"
                "• Contact support to set up reinvestment\n"
                "• Reinvest your ROI earnings for compound growth\n"
                "• Start new investment cycles with higher potential\n\n"
                "💡 **Note:** Detailed reinvestment history will be available in the next update!"
            )
            
            await callback.message.edit_text(
                reinvest_text,
                reply_markup=investment_history_kb(),
                parse_mode="Markdown"
            )
            
    except Exception as e:
        await callback.message.edit_text(
            f"❌ **Error loading reinvestment transactions:** {str(e)}",
            reply_markup=investment_history_kb(),
            parse_mode="Markdown"
        )
    
    await callback.answer()


@dp.callback_query(F.data == "back_to_main")
async def back_to_main_cb(callback: CallbackQuery):
    """Return to main menu"""
    await callback.message.edit_text(
        "🚀 **Investment Bot Menu**\n\n"
        "Choose an option from the menu below:",
        reply_markup=main_menu_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()


async def run_user_bot():
    """Run the user bot with proper session management"""
    try:
        print("🤖 Starting User Bot...")
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        print(f"❌ User Bot Error: {e}")
    finally:
        print("🛑 User Bot stopped")
        await bot.session.close()


async def stop_user_bot():
    """Gracefully stop the user bot"""
    try:
        await dp.stop_polling()
        await bot.session.close()
        print("✅ User Bot stopped gracefully")
    except Exception as e:
        print(f"❌ Error stopping User Bot: {e}")
