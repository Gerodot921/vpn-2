from __future__ import annotations

from dataclasses import dataclass
import os
from importlib import import_module

# Load .env automatically when available
try:
    import_module("dotenv").load_dotenv()
except Exception:
    # If python-dotenv is not installed, continue — env must be provided by the environment
    pass


@dataclass(frozen=True)
class Settings:
    bot_token: str
    payment_provider_token: str
    billing_currency: str
    mini_app_url: str
    
    # Xray API settings
    xray_api_host: str
    xray_api_port: int
    xray_admin_secret: str
    
    # 3x-ui settings
    three_x_ui_host: str
    three_x_ui_port: int
    three_x_ui_base_path: str
    three_x_ui_username: str
    three_x_ui_password: str
    three_x_ui_inbound_tag: str
    three_x_ui_inbound_port: int
    three_x_ui_inbound_protocol: str
    
    # VPN server endpoint (for client configs)
    vpn_endpoint_host: str
    vpn_endpoint_port: int
    
    # Subscription settings
    subscription_api_url: str  # Base URL of our FastAPI backend (for subscription management)
    
    debug: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        
        if not bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

        payment_provider_token = os.getenv("PAYMENT_PROVIDER_TOKEN", "").strip()
        billing_currency = os.getenv("BILLING_CURRENCY", "USD").strip().upper() or "USD"
        mini_app_url = os.getenv("TELEGRAM_MINI_APP_URL", "http://backend:8000/miniapp").strip()
        
        xray_api_host = os.getenv("XRAY_API_HOST", "xray").strip()
        xray_api_port = int(os.getenv("XRAY_API_PORT", "10085"))
        xray_admin_secret = os.getenv("XRAY_ADMIN_SECRET", "").strip()
        
        if not xray_admin_secret:
            raise RuntimeError("XRAY_ADMIN_SECRET is not set")
        
        three_x_ui_host = os.getenv("THREE_X_UI_HOST", "three-x-ui").strip()
        three_x_ui_port = int(os.getenv("THREE_X_UI_PORT", "7654"))
        three_x_ui_base_path = os.getenv("THREE_X_UI_BASE_PATH", "").strip()
        three_x_ui_username = os.getenv("THREE_X_UI_USERNAME", "admin").strip()
        three_x_ui_password = os.getenv("THREE_X_UI_PASSWORD", "").strip()
        three_x_ui_inbound_tag = os.getenv("THREE_X_UI_INBOUND_TAG", "bot-vless").strip()
        three_x_ui_inbound_port = int(os.getenv("THREE_X_UI_INBOUND_PORT", "11000"))
        three_x_ui_inbound_protocol = os.getenv("THREE_X_UI_INBOUND_PROTOCOL", "vless").strip().lower() or "vless"
        
        if not three_x_ui_password:
            raise RuntimeError("THREE_X_UI_PASSWORD is not set")
        
        vpn_endpoint_host = os.getenv("VPN_ENDPOINT_HOST", "").strip()
        vpn_endpoint_port = int(os.getenv("VPN_ENDPOINT_PORT", "11000"))
        
        if not vpn_endpoint_host:
            raise RuntimeError("VPN_ENDPOINT_HOST is not set")
        
        subscription_api_url = os.getenv("SUBSCRIPTION_API_URL", "http://backend:8000").strip()
        debug = os.getenv("DEBUG", "").lower() in ("1", "true", "yes")
        
        return cls(
            bot_token=bot_token,
            payment_provider_token=payment_provider_token,
            billing_currency=billing_currency,
            mini_app_url=mini_app_url,
            xray_api_host=xray_api_host,
            xray_api_port=xray_api_port,
            xray_admin_secret=xray_admin_secret,
            three_x_ui_host=three_x_ui_host,
            three_x_ui_port=three_x_ui_port,
            three_x_ui_base_path=three_x_ui_base_path,
            three_x_ui_username=three_x_ui_username,
            three_x_ui_password=three_x_ui_password,
            three_x_ui_inbound_tag=three_x_ui_inbound_tag,
            three_x_ui_inbound_port=three_x_ui_inbound_port,
            three_x_ui_inbound_protocol=three_x_ui_inbound_protocol,
            vpn_endpoint_host=vpn_endpoint_host,
            vpn_endpoint_port=vpn_endpoint_port,
            subscription_api_url=subscription_api_url,
            debug=debug,
        )
