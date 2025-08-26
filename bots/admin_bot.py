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
    list_support_tickets,
    create_user_with_access_code,
    list_users  # make sure this import exists
)

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
    kb.button(text="💰 Credit Balance", callback_data="credit_balance")
    kb.button(text="🎫 View Support Tickets", callback_data="view_tickets")
    kb.button(text="📊 List All Users", callback_data="list_users")
    kb.adjust(2, 2)
    return kb.as_markup()


@dp.message(Command("start"))
@admin_only
async def admin_start(message: Message):
    await message.answer(
        "🔐 Admin Dashboard\n\nWelcome! What would you like to do?",
        reply_markup=main_admin_kb()
    )


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


@dp.callback_query(F.data == "view_tickets")
@admin_callback_only
async def view_tickets(callback: CallbackQuery):
    with get_session() as session:
        tickets = list_support_tickets(session, limit=10)
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
🔐 Admin Commands:

📋 Registration Flow:
• Click "Register New User" button
• Follow the step-by-step prompts
• Get access code automatically

💰 Quick Actions:
• /credit <user_id> <amount> - Credit user balance
• /help - Show this help message

🎯 Features:
• User registration with full details
• Automatic access code generation
• Balance management
• Support ticket monitoring
• User listing
"""
    await message.answer(help_text)


async def run_admin_bot():
    await dp.start_polling(bot)
