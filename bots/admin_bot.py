from __future__ import annotations

from functools import wraps
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.config import settings
from app.db import get_session
from app.services import (
    create_user,
    credit_user_balance,
    get_support_tickets,
    create_user_with_access_code,
    list_users  # make sure this import exists
)
from scheduler.jobs import catchup_missed_roi
from datetime import datetime

bot = Bot(token=settings.admin_bot_token)
dp = Dispatcher()


class RegistrationStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_email = State()
    waiting_for_phone = State()
    waiting_for_country = State()
    waiting_for_balance = State()


def admin_only(func):
    @wraps(func)
    async def wrapper(message: Message, **kwargs):
        if message.from_user.id != settings.admin_chat_id:
            await message.answer("Unauthorized.")
            return
        return await func(message, **kwargs)
    return wrapper


def admin_callback_only(func):
    @wraps(func)
    async def wrapper(callback: CallbackQuery, **kwargs):
        if callback.from_user.id != settings.admin_chat_id:
            await callback.answer("Unauthorized.", show_alert=True)
            return
        return await func(callback, **kwargs)
    return wrapper


def main_admin_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="👤 Register New User", callback_data="register_user")
    kb.button(text="💰 Manage Balance", callback_data="manage_balance")
    kb.button(text="🎫 View Support Tickets", callback_data="view_tickets")
    kb.button(text="📊 List All Users", callback_data="list_users")
    kb.button(text="🔄 ROI Management", callback_data="roi_recovery")
    kb.button(text="📈 Manage ROI Cycles", callback_data="manage_roi_cycles")
    kb.button(text="⚙️ User Settings", callback_data="user_settings")
    kb.adjust(2, 2, 2, 1)
    return kb.as_markup()


def roi_recovery_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Catch Up Missed ROI", callback_data="catchup_roi")
    kb.button(text="📊 ROI Status Report", callback_data="roi_status_report")
    kb.button(text="⚡ Force ROI Payment", callback_data="force_roi")
    kb.button(text="📈 Adjust ROI Cycles", callback_data="adjust_roi_cycles")
    kb.button(text="🔙 Back to Main Menu", callback_data="back_to_main")
    kb.adjust(1, 1, 1, 1, 1)
    return kb.as_markup()


def balance_management_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="💰 Credit Balance", callback_data="credit_balance")
    kb.button(text="💸 Debit Balance", callback_data="debit_balance")
    kb.button(text="🔄 Transfer Between Users", callback_data="transfer_balance")
    kb.button(text="🔙 Back to Main Menu", callback_data="back_to_main")
    kb.adjust(1, 1, 1, 1)
    return kb.as_markup()


def user_settings_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="🔓 Enable Withdrawal", callback_data="enable_withdrawal")
    kb.button(text="🔒 Disable Withdrawal", callback_data="disable_withdrawal")
    kb.button(text="📅 Set Next ROI Date", callback_data="set_roi_date")
    kb.button(text="🔄 Reset ROI Cycles", callback_data="reset_roi_cycles")
    kb.button(text="🔙 Back to Main Menu", callback_data="back_to_main")
    kb.adjust(1, 1, 1, 1, 1)
    return kb.as_markup()


def roi_cycle_management_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="📈 Set ROI Cycles", callback_data="set_roi_cycles")
    kb.button(text="➕ Increment ROI Cycles", callback_data="increment_roi_cycles")
    kb.button(text="📊 View ROI Status", callback_data="roi_status_report")
    kb.button(text="🔓 Unlock Withdrawal", callback_data="unlock_withdrawal")
    kb.button(text="🔙 Back to Main Menu", callback_data="back_to_main")
    kb.adjust(1, 1, 1, 1, 1)
    return kb.as_markup()


@dp.message(Command("start"))
@admin_only
async def admin_start(message: Message):
    await message.answer(
        "🔐 Admin Dashboard\n\nWelcome! What would you like to do?",
        reply_markup=main_admin_kb()
    )


@dp.message(Command("catchup_roi"))
@admin_only
async def manual_catchup_roi_cmd(message: Message):
    """Manual command to catch up missed ROI payments"""
    await message.answer("🔄 Starting ROI catch-up process...")
    try:
        processed_users, total_payments = await catchup_missed_roi()
        if total_payments > 0:
            await message.answer(
                f"✅ ROI catch-up completed successfully!\n\n"
                f"👥 Users processed: {processed_users}\n"
                f"💰 Total payments recovered: {total_payments}\n\n"
                f"All missed ROI payments have been processed."
            )
        else:
            await message.answer("✅ No missed ROI payments found. All users are up to date!")
    except Exception as e:
        await message.answer(f"❌ ROI catch-up failed: {e}")


@dp.message(Command("roi_status"))
@admin_only
async def roi_status_cmd(message: Message):
    """Show ROI status for all users"""
    with get_session() as session:
        users = list_users(session)
        if not users:
            await message.answer("📊 No users found in the system.")
            return
        
        status_text = "📊 **ROI Status Report**\n\n"
        total_users = len(users)
        completed_users = 0
        active_users = 0
        
        for user in users:
            if user.roi_cycles_completed >= settings.max_roi_cycles:
                completed_users += 1
            elif user.roi_cycles_completed > 0:
                active_users += 1
            
            status_text += (
                f"👤 **{user.name}** (ID: {user.user_id})\n"
                f"   💰 Balance: {user.current_balance:.2f}\n"
                f"   📈 ROI Cycles: {user.roi_cycles_completed}/{settings.max_roi_cycles}\n"
                f"   ⏳ Next ROI: {user.next_roi_date.strftime('%Y-%m-%d') if user.next_roi_date else 'N/A'}\n"
                f"   🚪 Withdrawal: {'✅ Enabled' if user.can_withdraw else '❌ Disabled'}\n\n"
            )
        
        summary = (
            f"📈 **Summary**\n"
            f"Total Users: {total_users}\n"
            f"Active ROI: {active_users}\n"
            f"Completed: {completed_users}\n"
            f"Pending: {total_users - active_users - completed_users}"
        )
        
        await message.answer(status_text + summary, parse_mode="Markdown")


@dp.callback_query(F.data == "roi_recovery")
@admin_callback_only
async def roi_recovery_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔄 **ROI Recovery & Management**\n\n"
        "Choose an option to manage ROI processing:",
        reply_markup=roi_recovery_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data == "catchup_roi")
@admin_callback_only
async def catchup_roi_callback(callback: CallbackQuery):
    await callback.message.edit_text("🔄 Starting ROI catch-up process...")
    try:
        processed_users, total_payments = await catchup_missed_roi()
        if total_payments > 0:
            await callback.message.edit_text(
                f"✅ **ROI Catch-up Completed!**\n\n"
                f"👥 Users processed: {processed_users}\n"
                f"💰 Total payments recovered: {total_payments}\n\n"
                f"All missed ROI payments have been processed.",
                reply_markup=roi_recovery_kb(),
                parse_mode="Markdown"
            )
        else:
            await callback.message.edit_text(
                "✅ **No Missed ROI Found**\n\n"
                "All users are up to date with their ROI payments!",
                reply_markup=roi_recovery_kb(),
                parse_mode="Markdown"
            )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ **ROI Catch-up Failed**\n\n"
            f"Error: {e}\n\n"
            f"Please check the logs for more details.",
            reply_markup=roi_recovery_kb(),
            parse_mode="Markdown"
        )
    await callback.answer()


@dp.callback_query(F.data == "roi_status_report")
@admin_callback_only
async def roi_status_report_callback(callback: CallbackQuery):
    with get_session() as session:
        users = list_users(session)
        if not users:
            await callback.message.edit_text(
                "📊 No users found in the system.",
                reply_markup=roi_recovery_kb()
            )
            await callback.answer()
            return
        
        status_text = "📊 **ROI Status Report**\n\n"
        total_users = len(users)
        completed_users = 0
        active_users = 0
        
        for user in users:
            if user.roi_cycles_completed >= settings.max_roi_cycles:
                completed_users += 1
            elif user.roi_cycles_completed > 0:
                active_users += 1
            
            status_text += (
                f"👤 **{user.name}** (ID: {user.user_id})\n"
                f"   💰 Balance: {user.current_balance:.2f}\n"
                f"   📈 ROI Cycles: {user.roi_cycles_completed}/{settings.max_roi_cycles}\n"
                f"   ⏳ Next ROI: {user.next_roi_date.strftime('%Y-%m-%d') if user.next_roi_date else 'N/A'}\n"
                f"   🚪 Withdrawal: {'✅ Enabled' if user.can_withdraw else '❌ Disabled'}\n\n"
            )
        
        summary = (
            f"📈 **Summary**\n"
            f"Total Users: {total_users}\n"
            f"Active ROI: {active_users}\n"
            f"Completed: {completed_users}\n"
            f"Pending: {total_users - active_users - completed_users}"
        )
        
        await callback.message.edit_text(
            status_text + summary,
            reply_markup=roi_recovery_kb(),
            parse_mode="Markdown"
        )
    await callback.answer()


@dp.callback_query(F.data == "force_roi")
@admin_callback_only
async def force_roi_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        "⚡ **Force ROI Payment**\n\n"
        "Send the command in this format:\n"
        "`/force_roi <telegram_id>`\n\n"
        "This will immediately process ROI for the user if eligible.",
        reply_markup=roi_recovery_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data == "adjust_roi_cycles")
@admin_callback_only
async def adjust_roi_cycles_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        "📈 **Adjust ROI Cycles**\n\n"
        "Send the command in this format:\n"
        "`/adjust_roi <telegram_id> <cycles>`\n\n"
        "Example: `/adjust_roi 123456789 2` to set ROI cycles to 2",
        reply_markup=roi_recovery_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data == "manage_roi_cycles")
@admin_callback_only
async def manage_roi_cycles_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "📈 **ROI Cycle Management**\n\n"
        "Manage user ROI cycles and withdrawal access:\n\n"
        "• **Set ROI Cycles**: Set specific cycle number (0-4)\n"
        "• **Increment ROI Cycles**: Add +1 to current cycles\n"
        "• **View ROI Status**: Check all users' ROI progress\n"
        "• **Unlock Withdrawal**: Enable withdrawal for users at cycle 4\n\n"
        "💡 **Note**: Withdrawal is automatically unlocked when users reach 4 ROI cycles!",
        reply_markup=roi_cycle_management_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data == "set_roi_cycles")
@admin_callback_only
async def set_roi_cycles_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        "📈 **Set ROI Cycles**\n\n"
        "Set a user's ROI cycles to a specific number:\n\n"
        "**Command Format:**\n"
        "`/set_roi_cycles <telegram_id> <cycles>`\n\n"
        "**Examples:**\n"
        "• `/set_roi_cycles 123456789 0` - Reset to 0 cycles\n"
        "• `/set_roi_cycles 123456789 2` - Set to 2 cycles\n"
        "• `/set_roi_cycles 123456789 4` - Set to 4 cycles (unlocks withdrawal)\n\n"
        "💡 **Cycle Range**: 0 to 4 (4 cycles unlocks withdrawal)",
        reply_markup=roi_cycle_management_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data == "increment_roi_cycles")
@admin_callback_only
async def increment_roi_cycles_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        "➕ **Increment ROI Cycles**\n\n"
        "Add +1 to a user's current ROI cycles AND add ROI payment to balance:\n\n"
        "**Command Format:**\n"
        "`/increment_roi <telegram_id>`\n\n"
        "**What happens:**\n"
        "• Increments ROI cycles by +1\n"
        "• Adds 8% of initial balance to current balance\n"
        "• Records ROI payment in transaction history\n"
        "• Updates next ROI date\n\n"
        "**Examples:**\n"
        "• `/increment_roi 123456789` - Add +1 cycle + ROI payment\n\n"
        "💡 **Note**:\n"
        "• Cycles range from 0 to 4\n"
        "• Reaching 4 cycles automatically unlocks withdrawal\n"
        "• ROI payment = 8% of user's initial balance",
        reply_markup=roi_cycle_management_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data == "unlock_withdrawal")
@admin_callback_only
async def unlock_withdrawal_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔓 **Unlock Withdrawal**\n\n"
        "Enable withdrawal for users who have completed ROI cycles:\n\n"
        "**Command Format:**\n"
        "`/unlock_withdrawal <telegram_id>`\n\n"
        "**Examples:**\n"
        "• `/unlock_withdrawal 123456789` - Enable withdrawal\n\n"
        "💡 **Note**:\n"
        "• Withdrawal is automatically unlocked at 4 ROI cycles\n"
        "• Use this to manually enable withdrawal if needed\n"
        "• Users must have sufficient balance to withdraw",
        reply_markup=roi_cycle_management_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data == "manage_balance")
@admin_callback_only
async def manage_balance_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "💰 **Balance Management**\n\n"
        "Choose an option to manage user balances:",
        reply_markup=balance_management_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data == "debit_balance")
@admin_callback_only
async def debit_balance_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        "💸 **Debit Balance**\n\n"
        "Send the command in this format:\n"
        "`/debit <telegram_id> <amount>`\n\n"
        "Example: `/debit 123456789 50.00`",
        reply_markup=balance_management_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data == "transfer_balance")
@admin_callback_only
async def transfer_balance_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔄 **Transfer Balance**\n\n"
        "Send the command in this format:\n"
        "`/transfer <from_id> <to_id> <amount>`\n\n"
        "Example: `/transfer 123456789 987654321 100.00`",
        reply_markup=balance_management_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data == "user_settings")
@admin_callback_only
async def user_settings_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "⚙️ **User Settings Management**\n\n"
        "Choose an option to manage user settings:",
        reply_markup=user_settings_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data == "enable_withdrawal")
@admin_callback_only
async def enable_withdrawal_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔓 **Enable Withdrawal**\n\n"
        "Send the command in this format:\n"
        "`/enable_withdrawal <telegram_id>`\n\n"
        "This will allow the user to withdraw their balance.",
        reply_markup=user_settings_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data == "disable_withdrawal")
@admin_callback_only
async def disable_withdrawal_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔒 **Disable Withdrawal**\n\n"
        "Send the command in this format:\n"
        "`/disable_withdrawal <telegram_id>`\n\n"
        "This will prevent the user from withdrawing their balance.",
        reply_markup=user_settings_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data == "set_roi_date")
@admin_callback_only
async def set_roi_date_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        "📅 **Set Next ROI Date**\n\n"
        "Send the command in this format:\n"
        "`/set_roi_date <telegram_id> <days_from_now>`\n\n"
        "Example: `/set_roi_date 123456789 7` for 7 days from now",
        reply_markup=user_settings_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data == "reset_roi_cycles")
@admin_callback_only
async def reset_roi_cycles_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔄 **Reset ROI Cycles**\n\n"
        "Send the command in this format:\n"
        "`/reset_roi <telegram_id>`\n\n"
        "This will reset the user's ROI cycles to 0 and allow them to start fresh.",
        reply_markup=user_settings_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.callback_query(F.data == "back_to_main")
@admin_callback_only
async def back_to_main_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔐 Admin Dashboard\n\nWelcome! What would you like to do?",
        reply_markup=main_admin_kb()
    )
    await callback.answer()


@dp.callback_query(F.data == "register_user")
@admin_callback_only
async def start_registration(callback: CallbackQuery, state: FSMContext):
    await state.set_state(RegistrationStates.waiting_for_name)
    await callback.message.answer(
        "👤 User Registration\n\nPlease enter the user's full name:",
        reply_markup=ReplyKeyboardRemove()
    )
    await callback.answer()


@dp.message(StateFilter(RegistrationStates.waiting_for_name))
@admin_only
async def get_user_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(RegistrationStates.waiting_for_email)
    await message.answer("📧 Please enter the user's email address (or send '-' if none):")


@dp.message(StateFilter(RegistrationStates.waiting_for_email))
@admin_only
async def get_user_email(message: Message, state: FSMContext):
    email = message.text.strip() if message.text.strip() != "-" else None
    await state.update_data(email=email)
    await state.set_state(RegistrationStates.waiting_for_phone)
    await message.answer("📱 Please enter the user's phone number (or send '-' if none):")


@dp.message(StateFilter(RegistrationStates.waiting_for_phone))
@admin_only
async def get_user_phone(message: Message, state: FSMContext):
    phone = message.text.strip() if message.text.strip() != "-" else None
    await state.update_data(phone=phone)
    await state.set_state(RegistrationStates.waiting_for_country)
    await message.answer("🌍 Please enter the user's country (or send '-' if none):")


@dp.message(StateFilter(RegistrationStates.waiting_for_country))
@admin_only
async def get_user_country(message: Message, state: FSMContext):
    country = message.text.strip() if message.text.strip() != "-" else None
    await state.update_data(country=country)
    await state.set_state(RegistrationStates.waiting_for_balance)
    await message.answer("💰 Please enter the initial balance amount:")


@dp.message(StateFilter(RegistrationStates.waiting_for_balance))
@admin_only
async def get_user_balance(message: Message, state: FSMContext):
    try:
        balance = float(message.text.strip())
        if balance <= 0:
            await message.answer("❌ Balance must be greater than 0. Please try again:")
            return
    except ValueError:
        await message.answer("❌ Invalid balance amount. Please enter a valid number:")
        return

    user_data = await state.get_data()
    await state.clear()

    with get_session() as session:
        access_code, success_message = create_user_with_access_code(
            session,
            name=user_data['name'],
            initial_balance=balance,
            email=user_data['email'],
            phone=user_data['phone'],
            country=user_data['country']
        )

    await message.answer(
        success_message,
        parse_mode="Markdown",
        reply_markup=main_admin_kb()
    )


@dp.callback_query(F.data == "credit_balance")
@admin_callback_only
async def credit_balance_start(callback: CallbackQuery):
    await callback.message.answer(
        "💰 Credit Balance\n\nPlease send the command in this format:\n"
        "`/credit <telegram_id> <amount>`\n\nExample: `/credit 123456789 100.50`",
        parse_mode="Markdown"
    )
    await callback.answer()


@dp.message(Command("credit"))
@admin_only
async def cmd_credit(message: Message):
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Usage: /credit <telegram_id> <amount>")
        return
    try:
        telegram_id = int(parts[1])
        amount = float(parts[2])
    except Exception:
        await message.answer("Invalid parameters.")
        return
    with get_session() as session:
        user = credit_user_balance(session, telegram_id, amount)
        if not user:
            await message.answer("User not found.")
            return
    await message.answer(f"✅ Credited {amount:.2f}. New balance: {user.current_balance:.2f}")


@dp.message(Command("debit"))
@admin_only
async def cmd_debit(message: Message):
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Usage: /debit <telegram_id> <amount>")
        return
    try:
        telegram_id = int(parts[1])
        amount = float(parts[2])
    except Exception:
        await message.answer("Invalid parameters.")
        return
    with get_session() as session:
        from app.services import debit_user_balance
        user = debit_user_balance(session, telegram_id, amount)
        if not user:
            await message.answer("User not found or insufficient balance.")
            return
    await message.answer(f"✅ Debited {amount:.2f}. New balance: {user.current_balance:.2f}")


@dp.message(Command("transfer"))
@admin_only
async def cmd_transfer(message: Message):
    parts = (message.text or "").split(maxsplit=3)
    if len(parts) < 4:
        await message.answer("Usage: /transfer <from_id> <to_id> <amount>")
        return
    try:
        from_id = int(parts[1])
        to_id = int(parts[2])
        amount = float(parts[3])
    except Exception:
        await message.answer("Invalid parameters.")
        return
    with get_session() as session:
        from app.services import transfer_balance
        success, message_text = transfer_balance(session, from_id, to_id, amount)
        if not success:
            await message.answer(f"❌ Transfer failed: {message_text}")
            return
    await message.answer(f"✅ Transfer successful: {amount:.2f} from {from_id} to {to_id}")


@dp.message(Command("force_roi"))
@admin_only
async def cmd_force_roi(message: Message):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /force_roi <telegram_id>")
        return
    try:
        telegram_id = int(parts[1])
    except Exception:
        await message.answer("Invalid telegram ID.")
        return
    with get_session() as session:
        from app.services import force_roi_payment
        success, message_text = force_roi_payment(session, telegram_id)
        if not success:
            await message.answer(f"❌ Force ROI failed: {message_text}")
            return
    await message.answer(f"✅ Force ROI successful: {message_text}")


@dp.message(Command("adjust_roi"))
@admin_only
async def cmd_adjust_roi(message: Message):
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Usage: /adjust_roi <telegram_id> <cycles>")
        return
    try:
        telegram_id = int(parts[1])
        cycles = int(parts[2])
    except Exception:
        await message.answer("Invalid parameters.")
        return
    with get_session() as session:
        from app.services import adjust_roi_cycles
        success, message_text = adjust_roi_cycles(session, telegram_id, cycles)
        if not success:
            await message.answer(f"❌ ROI adjustment failed: {message_text}")
            return
    await message.answer(f"✅ ROI cycles adjusted: {message_text}")


@dp.message(Command("enable_withdrawal"))
@admin_only
async def cmd_enable_withdrawal(message: Message):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /enable_withdrawal <telegram_id>")
        return
    try:
        telegram_id = int(parts[1])
    except Exception:
        await message.answer("Invalid telegram ID.")
        return
    with get_session() as session:
        from app.services import enable_user_withdrawal
        success, message_text = enable_user_withdrawal(session, telegram_id)
        if not success:
            await message.answer(f"❌ Failed to enable withdrawal: {message_text}")
            return
    await message.answer(f"✅ Withdrawal enabled for user {telegram_id}")


@dp.message(Command("disable_withdrawal"))
@admin_only
async def cmd_disable_withdrawal(message: Message):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /disable_withdrawal <telegram_id>")
        return
    try:
        telegram_id = int(parts[1])
    except Exception:
        await message.answer("Invalid telegram ID.")
        return
    with get_session() as session:
        from app.services import disable_user_withdrawal
        success, message_text = disable_user_withdrawal(session, telegram_id)
        if not success:
            await message.answer(f"❌ Failed to disable withdrawal: {message_text}")
            return
    await message.answer(f"✅ Withdrawal disabled for user {telegram_id}")


@dp.message(Command("set_roi_date"))
@admin_only
async def cmd_set_roi_date(message: Message):
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Usage: /set_roi_date <telegram_id> <days_from_now>")
        return
    try:
        telegram_id = int(parts[1])
        days = int(parts[2])
    except Exception:
        await message.answer("Invalid parameters.")
        return
    with get_session() as session:
        from app.services import set_next_roi_date
        success, message_text = set_next_roi_date(session, telegram_id, days)
        if not success:
            await message.answer(f"❌ Failed to set ROI date: {message_text}")
            return
    await message.answer(f"✅ Next ROI date set: {message_text}")


@dp.message(Command("reset_roi"))
@admin_only
async def cmd_reset_roi(message: Message):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /reset_roi <telegram_id>")
        return
    try:
        telegram_id = int(parts[1])
    except Exception:
        await message.answer("Invalid telegram ID.")
        return
    with get_session() as session:
        from app.services import reset_user_roi_cycles
        success, message_text = reset_user_roi_cycles(session, telegram_id)
        if not success:
            await message.answer(f"❌ Failed to reset ROI cycles: {message_text}")
            return
    await message.answer(f"✅ ROI cycles reset for user {telegram_id}")


@dp.message(Command("set_roi_cycles"))
@admin_only
async def cmd_set_roi_cycles(message: Message):
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("Usage: /set_roi_cycles <telegram_id> <cycles>")
        return
    try:
        telegram_id = int(parts[1])
        cycles = int(parts[2])
    except Exception:
        await message.answer("Invalid parameters.")
        return
    with get_session() as session:
        from app.services import adjust_roi_cycles
        success, message_text = adjust_roi_cycles(session, telegram_id, cycles)
        if not success:
            await message.answer(f"❌ Failed to set ROI cycles: {message_text}")
            return
    await message.answer(f"✅ ROI cycles set to {cycles} for user {telegram_id}")


@dp.message(Command("increment_roi"))
@admin_only
async def cmd_increment_roi(message: Message):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /increment_roi <telegram_id>")
        return
    try:
        telegram_id = int(parts[1])
    except Exception:
        await message.answer("Invalid telegram ID.")
        return
    with get_session() as session:
        from app.services import increment_roi_cycles
        from app.config import settings
        
        # Debug: Show database URL
        debug_info = f"\n\n🔍 **Debug Info:**\nDatabase: {settings.database_url[:50]}..."
        
        success, message_text = increment_roi_cycles(session, telegram_id)
        if not success:
            await message.answer(f"❌ Failed to increment ROI cycles: {message_text}{debug_info}")
            return
        
        # Get updated user info to verify changes
        from app.models import User
        user = session.query(User).filter(User.user_id == telegram_id).first()
        if user:
            verification_text = f"\n\n📊 **Verification:**\nBalance: {user.current_balance:.2f}\nCycles: {user.roi_cycles_completed}/4"
            await message.answer(f"✅ {message_text}{verification_text}{debug_info}")
        else:
            await message.answer(f"✅ {message_text}{debug_info}")


@dp.message(Command("debug_db"))
@admin_only
async def cmd_debug_db(message: Message):
    """Debug database connection and show current status"""
    import os
    from app.config import settings
    from app.db import engine
    from sqlalchemy import text
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1 as test"))
            db_test = result.fetchone()[0]
        
        with get_session() as session:
            from app.models import User
            user_count = session.query(User).count()
            
        debug_text = (
            f"🔍 **Database Debug Info**\n\n"
            f"📊 Database URL: `{settings.database_url}`\n"
            f"✅ Connection Test: {db_test}\n"
            f"👥 Total Users: {user_count}\n"
            f"🌍 Environment: {os.getenv('ENV', 'production')}"
        )
        
        await message.answer(debug_text, parse_mode="Markdown")
        
    except Exception as e:
        await message.answer(f"❌ Database debug failed: {e}")


@dp.message(Command("unlock_withdrawal"))
@admin_only
async def cmd_unlock_withdrawal(message: Message):
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Usage: /unlock_withdrawal <telegram_id>")
        return
    try:
        telegram_id = int(parts[1])
    except Exception:
        await message.answer("Invalid telegram ID.")
        return
    with get_session() as session:
        from app.services import enable_user_withdrawal
        success, message_text = enable_user_withdrawal(session, telegram_id)
        if not success:
            await message.answer(f"❌ Failed to unlock withdrawal: {message_text}")
            return
    await message.answer(f"✅ Withdrawal unlocked for user {telegram_id}")


@dp.callback_query(F.data == "view_tickets")
@admin_callback_only
async def view_tickets(callback: CallbackQuery):
    with get_session() as session:
        tickets = get_support_tickets(session, limit=10)
    if not tickets:
        await callback.message.answer("📭 No support tickets found.")
        await callback.answer()
        return

    lines = ["🎫 Recent Support Tickets:\n"]
    for t in tickets:
        lines.append(f"#{t.ticket_id[:8]} | User: {t.user_id} | {t.created_at:%Y-%m-%d %H:%M}\n{t.message[:100]}...")

    await callback.message.answer("\n\n".join(lines))
    await callback.answer()


@dp.callback_query(F.data == "list_users")
@admin_callback_only
async def list_users_callback(callback: CallbackQuery):
    with get_session() as session:
        users = list_users(session)
    if not users:
        await callback.message.answer("👥 No users found.")
        await callback.answer()
        return

    lines = ["👥 Registered Users:\n"]
    for u in users:
        lines.append(f"ID: {u.user_id} | {u.name} | Balance: {u.current_balance:.2f} | ROI: {u.roi_cycles_completed}/4")

    await callback.message.answer("\n".join(lines))
    await callback.answer()


@dp.message(Command("help"))
@admin_only
async def admin_help(message: Message):
    help_text = """
🔐 **Admin Commands**

📋 **Registration Flow:**
• Click "Register New User" button
• Follow the step-by-step prompts
• Get access code automatically

💰 **Balance Management:**
• `/credit <user_id> <amount>` - Credit user balance
• `/debit <user_id> <amount>` - Debit user balance
• `/transfer <from_id> <to_id> <amount>` - Transfer between users

📈 **ROI Cycle Management:**
• `/set_roi_cycles <user_id> <cycles>` - Set specific ROI cycles (0-4)
• `/increment_roi <user_id>` - Add +1 to current ROI cycles
• `/adjust_roi <user_id> <cycles>` - Adjust ROI cycles
• `/reset_roi <user_id>` - Reset ROI cycles to 0
• `/unlock_withdrawal <user_id>` - Manually enable withdrawal

🔄 **ROI Management:**
• `/force_roi <user_id>` - Force immediate ROI payment
• `/set_roi_date <user_id> <days>` - Set next ROI date

⚙️ **User Settings:**
• `/enable_withdrawal <user_id>` - Enable user withdrawal
• `/disable_withdrawal <user_id>` - Disable user withdrawal

🎯 **Features:**
• User registration with full details
• Automatic access code generation
• Comprehensive balance management
• Support ticket monitoring
• User listing and management
• ROI recovery and management
• **Automatic withdrawal unlock at 4 ROI cycles! 🎉**
"""
    await message.answer(help_text, parse_mode="Markdown")


async def run_admin_bot():
    """Run the admin bot with proper session management"""
    try:
        print("🔐 Starting Admin Bot...")
        # Add process ID for debugging
        import os
        print(f"🆔 Process ID: {os.getpid()}")
        print(f"🆔 Bot Token: {bot.token[:10]}...")
        
        # Use skip_updates=True and add conflict handling
        await dp.start_polling(
            bot, 
            skip_updates=True,
            allowed_updates=["message", "callback_query", "chat_member"]
        )
    except Exception as e:
        print(f"❌ Admin Bot Error: {e}")
        if "Conflict: terminated by other getUpdates request" in str(e):
            print("⚠️  Bot conflict detected - another instance may be running")
        raise
    finally:
        print("🛑 Admin Bot stopped")
        await bot.session.close()


async def stop_admin_bot():
    """Gracefully stop the admin bot"""
    try:
        await dp.stop_polling()
        await bot.session.close()
        print("✅ Admin Bot stopped gracefully")
    except Exception as e:
        print(f"❌ Error stopping Admin Bot: {e}")
