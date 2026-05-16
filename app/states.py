"""FSM states for Telegram bot"""

from aiogram.fsm.state import State, StatesGroup


class ConfigFlow(StatesGroup):
    """States for config generation flow"""
    waiting_for_protocol = State()
    waiting_for_format = State()
    waiting_confirmation = State()


class AccountFlow(StatesGroup):
    """States for account management"""
    viewing_account = State()
    managing_subscriptions = State()


class BillingFlow(StatesGroup):
    """States for billing"""
    viewing_plans = State()
    choosing_plan = State()
