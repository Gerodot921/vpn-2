"""Telegram bot keyboards"""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Main menu keyboard"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚀 Quick Config")],
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
