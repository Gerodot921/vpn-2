"""
Telegram bot for Xray VPN subscription management
"""

from __future__ import annotations

import asyncio
import logging
import uuid
import qrcode
from io import BytesIO

import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from aiogram.enums import ParseMode

from .config import Settings
from .xray_api import XrayClient, generate_vless_config, generate_vmess_config
from .keyboards import main_menu_keyboard, protocol_keyboard, format_keyboard, yes_no_keyboard
from .states import ConfigFlow, AccountFlow, BillingFlow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    """Start command handler"""
    await message.answer(
        "👋 Welcome to Xray VPN Bot!\n\n"
        "This bot helps you manage your VPN subscriptions.\n\n"
        "Choose an option:",
        reply_markup=main_menu_keyboard(),
    )


@router.message(F.text == "🚀 Quick Config")
async def quick_config(message: Message, state: FSMContext) -> None:
    """Start quick config generation"""
    await state.set_state(ConfigFlow.waiting_for_protocol)
    await message.answer(
        "Choose a protocol for your VPN config:",
        reply_markup=protocol_keyboard(),
    )


@router.callback_query(F.data.startswith("protocol_"), ConfigFlow.waiting_for_protocol)
async def choose_protocol(callback: CallbackQuery, state: FSMContext) -> None:
    """Choose VPN protocol"""
    protocol = callback.data.replace("protocol_", "")
    await state.update_data(protocol=protocol)
    await state.set_state(ConfigFlow.waiting_for_format)
    await callback.message.edit_text(
        f"You selected: {protocol.upper()}\n\nChoose config format:",
        reply_markup=format_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("format_"), ConfigFlow.waiting_for_format)
async def choose_format(callback: CallbackQuery, state: FSMContext) -> None:
    """Choose config format"""
    format_type = callback.data.replace("format_", "")
    await state.update_data(format=format_type)
    await state.set_state(ConfigFlow.waiting_confirmation)
    
    data = await state.get_data()
    protocol = data.get("protocol", "vless")
    
    await callback.message.edit_text(
        f"Protocol: {protocol.upper()}\nFormat: {format_type}\n\nProceed?",
        reply_markup=yes_no_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "yes", ConfigFlow.waiting_confirmation)
async def generate_config(callback: CallbackQuery, state: FSMContext) -> None:
    """Generate and send config"""
    await callback.message.edit_text("⏳ Generating your config...")
    
    try:
        data = await state.get_data()
        protocol = data.get("protocol", "vless")
        format_type = data.get("format", "link")
        
        settings = Settings.from_env()
        user_id = str(callback.from_user.id)
        user_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{user_id}@vpn"))
        user_email = f"tg_{callback.from_user.id}"
        
        # Generate config based on protocol
        if protocol == "vless":
            config_str = await generate_vless_config(settings, user_uuid, user_email)
        elif protocol == "vmess":
            config_str = await generate_vmess_config(settings, user_uuid, user_email)
        else:
            await callback.message.edit_text("❌ Protocol not yet supported")
            await state.clear()
            return
        
        # Send based on format
        if format_type == "link":
            await callback.message.edit_text(
                f"<code>{config_str}</code>",
                parse_mode=ParseMode.HTML,
            )
        elif format_type == "qr":
            qr = qrcode.QRCode(version=1, box_size=10)
            qr.add_data(config_str)
            qr.make()
            
            img = qr.make_image(fill_color="black", back_color="white")
            img_bytes = BytesIO()
            img.save(img_bytes, format="PNG")
            img_bytes.seek(0)
            
            await callback.message.delete()
            await callback.message.answer_photo(
                photo=BufferedInputFile(img_bytes.read(), filename="config_qr.png"),
                caption=f"<code>{config_str}</code>",
                parse_mode=ParseMode.HTML,
            )
        elif format_type == "json":
            if protocol == "vmess":
                await callback.message.edit_text(
                    f"<code>{config_str}</code>",
                    parse_mode=ParseMode.HTML,
                )
            else:
                await callback.message.edit_text("JSON format available only for VMess")
        
        await state.clear()
    
    except Exception as e:
        logger.error(f"Config generation error: {e}")
        await callback.message.edit_text(f"❌ Error: {str(e)}")
        await state.clear()


@router.callback_query(F.data == "no", ConfigFlow.waiting_confirmation)
async def cancel_config(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel config generation"""
    await callback.message.edit_text("Cancelled. Choose an option:", reply_markup=main_menu_keyboard())
    await state.clear()


@router.message(F.text == "📊 My Account")
async def my_account(message: Message, state: FSMContext) -> None:
    """Show account info"""
    user_id = message.from_user.id
    user_name = message.from_user.username or message.from_user.first_name or "User"
    
    try:
        settings = Settings.from_env()
        
        account_info = (
            f"👤 <b>Account Info</b>\n\n"
            f"ID: <code>{user_id}</code>\n"
            f"Name: {user_name}\n\n"
            f"📊 Subscription Status: Active ✅\n"
            f"Expires: 30 days remaining\n\n"
            f"VPN Endpoint: <code>{settings.vpn_endpoint_host}:{settings.vpn_endpoint_port}</code>"
        )
        
        await message.answer(account_info, parse_mode=ParseMode.HTML)
    
    except Exception as e:
        logger.error(f"Account info error: {e}")
        await message.answer(f"❌ Error: {str(e)}")


@router.message(F.text == "💳 Billing")
async def billing(message: Message) -> None:
    """Show billing/plans"""
    billing_info = (
        "💳 <b>Billing & Plans</b>\n\n"
        "📱 <b>Available Plans:</b>\n\n"
        "🟢 <b>Basic (1 month)</b>\n"
        "Price: $5 USD\n"
        "Bandwidth: Unlimited\n"
        "Connections: 2\n\n"
        "🟠 <b>Pro (3 months)</b>\n"
        "Price: $12 USD\n"
        "Bandwidth: Unlimited\n"
        "Connections: 5\n\n"
        "🔴 <b>Premium (1 year)</b>\n"
        "Price: $40 USD\n"
        "Bandwidth: Unlimited\n"
        "Connections: 10\n\n"
        "Use /subscribe to purchase a plan"
    )
    
    await message.answer(billing_info, parse_mode=ParseMode.HTML)


@router.message(F.text == "⚙️ Settings")
async def settings(message: Message) -> None:
    """Show settings"""
    await message.answer(
        "⚙️ <b>Settings</b>\n\n"
        "Current settings:\n"
        "• Language: English 🇺🇸\n"
        "• Notifications: Enabled\n"
        "• Theme: Auto\n\n"
        "Use /help for more commands",
        parse_mode=ParseMode.HTML,
    )


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    """Show help"""
    await message.answer(
        "/start - Show main menu\n"
        "/quickconfig - Generate VPN config\n"
        "/account - Show account info\n"
        "/subscribe - Subscribe to a plan\n"
        "/help - Show this message",
    )


@router.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext) -> None:
    """Cancel current operation"""
    await state.clear()
    await message.answer("Operation cancelled", reply_markup=main_menu_keyboard())


async def main():
    """Main bot entry point"""
    settings = Settings.from_env()
    
    bot = Bot(token=settings.bot_token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    dp.include_router(router)
    
    try:
        logger.info("Starting Telegram bot...")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
