"""
Telegram bot for Xray VPN subscription management
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from io import BytesIO

import qrcode
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    LabeledPrice,
    Message,
    PreCheckoutQuery,
)
from aiogram.enums import ParseMode

from .config import Settings
from .billing import build_invoice_payload, get_plan, parse_invoice_payload, plan_summary_lines
from .three_x_ui import ThreeXUIClient
from .xray_api import generate_vless_config, generate_vmess_config
from .keyboards import main_menu_keyboard, protocol_keyboard, format_keyboard, yes_no_keyboard, buy_plan_keyboard
from .states import ConfigFlow, AccountFlow, BillingFlow

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()
_APP_SETTINGS: Settings | None = None


def get_settings() -> Settings:
    global _APP_SETTINGS
    if _APP_SETTINGS is None:
        _APP_SETTINGS = Settings.from_env()
    return _APP_SETTINGS



@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    """Start command handler"""
    settings = get_settings()
    await message.answer(
        "👋 Welcome to Xray VPN Bot!\n\n"
        "This bot helps you buy VPN access, receive configs, and manage subscriptions.\n\n"
        "Choose an option:",
        reply_markup=main_menu_keyboard(settings.mini_app_url),
    )


@router.message(Command("buy"))
async def buy_command(message: Message) -> None:
    lines = [f"• {line}" for line in plan_summary_lines()]
    await message.answer(
        "💳 <b>Plans</b>\n\n" + "\n".join(lines) + "\n\nOpen the mini app to pay and get access.",
        parse_mode=ParseMode.HTML,
        reply_markup=buy_plan_keyboard(),
    )


@router.callback_query(F.data == "open_mini_app")
async def open_mini_app(callback: CallbackQuery) -> None:
    settings = get_settings()
    await callback.message.answer(
        f"Open the mini app here: {settings.mini_app_url}",
    )
    await callback.answer()


@router.message(F.web_app_data)
async def web_app_data_handler(message: Message) -> None:
    settings = get_settings()
    if not message.web_app_data or not message.web_app_data.data:
        return
    try:
        payload = json.loads(message.web_app_data.data)
    except json.JSONDecodeError:
        await message.answer("❌ Invalid mini app payload.")
        return

    if payload.get("action") != "buy":
        await message.answer("❌ Unknown mini app action.")
        return

    plan = get_plan(str(payload.get("plan_id", "")))
    if not plan:
        await message.answer("❌ Unknown plan.")
        return

    if not settings.payment_provider_token:
        await message.answer(
            "🧾 Payment is not configured yet. Set PAYMENT_PROVIDER_TOKEN on the bot container and try again.",
            reply_markup=buy_plan_keyboard(),
        )
        return

    await message.bot.send_invoice(
        chat_id=message.chat.id,
        title=f"SkullVPN {plan.title}",
        description=f"{plan.duration_days} days access",
        payload=build_invoice_payload(plan.plan_id, message.from_user.id),
        provider_token=settings.payment_provider_token,
        currency=settings.billing_currency,
        prices=[LabeledPrice(label=plan.title, amount=plan.price_cents)],
        start_parameter=f"vpn-{plan.plan_id}",
    )


@router.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery) -> None:
    payload = parse_invoice_payload(query.invoice_payload)
    plan = get_plan(payload[0]) if payload else None
    if not plan:
        await query.answer(ok=False, error_message="Unknown payment payload")
        return
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message) -> None:
    settings = get_settings()
    if not message.successful_payment:
        return

    parsed = parse_invoice_payload(message.successful_payment.invoice_payload)
    if not parsed:
        await message.answer("❌ Payment payload is invalid.")
        return

    plan = get_plan(parsed[0])
    if not plan:
        await message.answer("❌ Purchased plan is unknown.")
        return

    try:
        async with ThreeXUIClient(settings) as client:
            access = await client.provision_purchase_access(message.from_user.id, plan)
    except Exception as exc:
        logger.exception("Failed to provision 3x-ui access")
        await message.answer(f"✅ Payment received, but access provisioning failed: {exc}")
        return

    qr = qrcode.QRCode(version=1, box_size=10, border=2)
    qr.add_data(access.access_link)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    image_bytes = BytesIO()
    image.save(image_bytes, format="PNG")
    image_bytes.seek(0)

    await message.answer_photo(
        photo=BufferedInputFile(image_bytes.read(), filename="vpn_access.png"),
        caption=(
            f"✅ <b>Access activated</b>\n\n"
            f"Plan: <b>{plan.title}</b> ({plan.duration_days} days)\n"
            f"Email: <code>{access.email}</code>\n"
            f"Link: <code>{access.access_link}</code>\n\n"
            f"Open it in your client or scan the QR."
        ),
        parse_mode=ParseMode.HTML,
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
    settings = get_settings()
    billing_info = "💳 <b>Billing & Plans</b>\n\n" + "\n".join(f"• {line}" for line in plan_summary_lines())
    await message.answer(
        billing_info,
        parse_mode=ParseMode.HTML,
        reply_markup=main_menu_keyboard(settings.mini_app_url),
    )


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
    global _APP_SETTINGS
    _APP_SETTINGS = settings
    
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
