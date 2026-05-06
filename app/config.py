from __future__ import annotations

from dataclasses import dataclass
import os
from urllib.parse import urlparse

# Load .env automatically when available
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # If python-dotenv is not installed, continue — env must be provided by the environment
    pass


@dataclass(frozen=True)
class Settings:
    bot_token: str
    generator_api_base_url: str

    @classmethod
    def from_env(cls) -> "Settings":
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        generator_api_base_url = os.getenv("GENERATOR_API_BASE_URL", "https://valokda-amnezia.vercel.app").strip()

        if not bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

        parsed = urlparse(generator_api_base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise RuntimeError("GENERATOR_API_BASE_URL must be a valid http(s) URL")

        return cls(bot_token=bot_token, generator_api_base_url=generator_api_base_url.rstrip("/"))
