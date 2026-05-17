"""3x-ui API client used by the Telegram bot to create VPN access."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any

import aiohttp

from .billing import PlanOffer
from .config import Settings

logger = logging.getLogger(__name__)


class ThreeXUIError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProvisionedAccess:
    inbound_id: int
    client_id: str
    email: str
    access_link: str
    config_json: str


class ThreeXUIClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        base_path = settings.three_x_ui_base_path.strip()
        if base_path and not base_path.startswith("/"):
            base_path = "/" + base_path
        self.base_path = base_path.rstrip("/")
        self.api_root = f"http://{settings.three_x_ui_host}:{settings.three_x_ui_port}"
        self._session: aiohttp.ClientSession | None = None
        self._csrf_token: str | None = None

    def _url(self, path: str) -> str:
        normalized = path if path.startswith("/") else f"/{path}"
        return f"{self.api_root}{self.base_path}{normalized}"

    async def __aenter__(self) -> "ThreeXUIClient":
        self._session = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True))
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True))
        return self._session

    async def _read_json(self, response: aiohttp.ClientResponse) -> dict[str, Any]:
        try:
            payload = await response.json(content_type=None)
        except Exception:
            text = await response.text()
            raise ThreeXUIError(f"Unexpected non-JSON response: {text[:250]}")
        if not isinstance(payload, dict):
            raise ThreeXUIError("Unexpected response format from 3x-ui")
        return payload

    async def _get(self, path: str) -> dict[str, Any]:
        session = await self._ensure_session()
        headers = {}
        if self._csrf_token:
            headers["X-CSRF-Token"] = self._csrf_token
        async with session.get(self._url(path), headers=headers) as response:
            payload = await self._read_json(response)
            if response.status >= 400 or payload.get("success") is False:
                raise ThreeXUIError(payload.get("msg") or f"3x-ui GET {path} failed")
            return payload

    async def _post(self, path: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
        session = await self._ensure_session()
        headers = {}
        if self._csrf_token:
            headers["X-CSRF-Token"] = self._csrf_token
        async with session.post(self._url(path), json=data or {}, headers=headers) as response:
            payload = await self._read_json(response)
            if response.status >= 400 or payload.get("success") is False:
                raise ThreeXUIError(payload.get("msg") or f"3x-ui POST {path} failed")
            return payload

    async def login(self) -> None:
        session = await self._ensure_session()
        csrf = await self._get("/csrf-token")
        token = csrf.get("obj")
        if not isinstance(token, str) or not token:
            raise ThreeXUIError("Could not mint 3x-ui CSRF token")
        self._csrf_token = token
        async with session.post(
            self._url("/login"),
            json={"username": self.settings.three_x_ui_username, "password": self.settings.three_x_ui_password},
            headers={"X-CSRF-Token": self._csrf_token},
        ) as response:
            payload = await self._read_json(response)
            if response.status >= 400 or payload.get("success") is False:
                raise ThreeXUIError(payload.get("msg") or "3x-ui login failed")

    async def ensure_authenticated(self) -> None:
        if self._csrf_token is None:
            await self.login()

    async def list_inbounds(self) -> list[dict[str, Any]]:
        await self.ensure_authenticated()
        payload = await self._get("/panel/api/inbounds/list")
        obj = payload.get("obj")
        return obj if isinstance(obj, list) else []

    async def get_inbound_by_port(self, port: int) -> dict[str, Any] | None:
        for inbound in await self.list_inbounds():
            try:
                if int(inbound.get("port", -1)) == int(port):
                    return inbound
            except Exception:
                continue
        return None

    async def ensure_vless_purchase_inbound(self) -> dict[str, Any]:
        existing = await self.get_inbound_by_port(self.settings.three_x_ui_inbound_port)
        if existing:
            return existing

        payload = {
            "enable": True,
            "remark": f"{self.settings.three_x_ui_inbound_tag} ({self.settings.three_x_ui_inbound_port})",
            "listen": "",
            "port": self.settings.three_x_ui_inbound_port,
            "protocol": self.settings.three_x_ui_inbound_protocol,
            "expiryTime": 0,
            "total": 0,
            "settings": json.dumps({"clients": [], "decryption": "none", "fallbacks": []}),
            "streamSettings": json.dumps({"network": "tcp", "security": "none"}),
            "sniffing": json.dumps({"enabled": True, "destOverride": ["http", "tls"]}),
        }
        await self._post("/panel/api/inbounds/add", payload)
        created = await self.get_inbound_by_port(self.settings.three_x_ui_inbound_port)
        if not created:
            raise ThreeXUIError("3x-ui inbound was created but could not be reloaded")
        return created

    async def get_client_traffic_by_email(self, email: str) -> dict[str, Any] | None:
        try:
            await self.ensure_authenticated()
            session = await self._ensure_session()
            headers = {}
            if self._csrf_token:
                headers["X-CSRF-Token"] = self._csrf_token
            async with session.get(self._url(f"/panel/api/inbounds/getClientTraffics/{email}"), headers=headers) as response:
                payload = await self._read_json(response)
                if response.status == 404 or payload.get("success") is False:
                    return None
                obj = payload.get("obj")
                return obj if isinstance(obj, dict) else None
        except ThreeXUIError:
            return None

    @staticmethod
    def _client_uuid(telegram_user_id: int) -> str:
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, f"tg:{telegram_user_id}"))

    async def provision_purchase_access(self, telegram_user_id: int, plan: PlanOffer) -> ProvisionedAccess:
        inbound = await self.ensure_vless_purchase_inbound()
        email = f"tg_{telegram_user_id}"
        client_uuid = self._client_uuid(telegram_user_id)
        expiry_ms = int(time.time() * 1000) + plan.duration_days * 24 * 60 * 60 * 1000
        client_json = {
            "id": client_uuid,
            "email": email,
            "limitIp": 0,
            "totalGB": 0,
            "expiryTime": expiry_ms,
            "enable": True,
            "flow": "",
            "tgId": telegram_user_id,
            "subId": f"tg{telegram_user_id}",
            "comment": plan.title,
            "reset": 0,
        }
        payload = {
            "id": int(inbound["id"]),
            "settings": json.dumps({"clients": [client_json]}),
        }

        existing = await self.get_client_traffic_by_email(email)
        if existing:
            await self._post(f"/panel/api/inbounds/updateClient/{client_uuid}", payload)
        else:
            await self._post("/panel/api/inbounds/addClient", payload)

        access_link = (
            f"vless://{client_uuid}@{self.settings.vpn_endpoint_host}:{self.settings.vpn_endpoint_port}"
            f"?type=tcp&security=none#{email}"
        )
        return ProvisionedAccess(
            inbound_id=int(inbound["id"]),
            client_id=client_uuid,
            email=email,
            access_link=access_link,
            config_json=json.dumps({
                "v": "2",
                "ps": email,
                "add": self.settings.vpn_endpoint_host,
                "port": self.settings.vpn_endpoint_port,
                "id": client_uuid,
                "aid": 0,
                "net": "tcp",
                "type": "none",
                "host": "",
                "path": "",
                "tls": "",
                "sni": "",
            }),
        )
