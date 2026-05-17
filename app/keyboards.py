"""Telegram bot keyboards"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.types import WebAppInfo


def main_menu_keyboard(mini_app_url: str | None = None) -> ReplyKeyboardMarkup:
    """Main menu keyboard"""
    first_row = [KeyboardButton(text="🚀 Quick Config")]
    if mini_app_url:
        first_row.insert(0, KeyboardButton(text="🛒 Open Mini App", web_app=WebAppInfo(url=mini_app_url)))

    return ReplyKeyboardMarkup(
        keyboard=[
            first_row,
            [KeyboardButton(text="📊 My Account")],
            [KeyboardButton(text="💳 Billing")],
            [KeyboardButton(text="⚙️ Settings")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def protocol_keyboard() -> InlineKeyboardMarkup:
    """Choose VPN protocol"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="VLESS", callback_data="protocol_vless")],
            [InlineKeyboardButton(text="VMess", callback_data="protocol_vmess")],
            [InlineKeyboardButton(text="Trojan", callback_data="protocol_trojan")],
        ]
    )


def format_keyboard() -> InlineKeyboardMarkup:
    """Choose config format"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Link", callback_data="format_link")],
            [InlineKeyboardButton(text="QR Code", callback_data="format_qr")],
            [InlineKeyboardButton(text="JSON", callback_data="format_json")],
        ]
    )


def yes_no_keyboard() -> InlineKeyboardMarkup:
    """Yes/No keyboard"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Yes", callback_data="yes"),
                InlineKeyboardButton(text="❌ No", callback_data="no"),
            ]
        ]
    )


def buy_plan_keyboard() -> InlineKeyboardMarkup:
    """Open the mini app from chat."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛒 Open Mini App", callback_data="open_mini_app")],
        ]
    )
