"""
Xray API client for managing inbounds (users, subscriptions, etc.)
Communicates with Xray core via gRPC-like protocol
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

import aiohttp

from .config import Settings

logger = logging.getLogger(__name__)


class XrayClient:
    """Client for Xray API communication"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.api_url = f"http://{settings.xray_api_host}:{settings.xray_api_port}"
        self.base_headers = {
            "Authorization": f"Bearer {settings.xray_admin_secret}",
            "Content-Type": "application/json",
        }
    
    async def create_vless_inbound(
        self,
        inbound_tag: str,
        port: int,
        clients: list[dict],
        fallbacks: Optional[dict] = None,
    ) -> dict:
        """
        Create a VLESS inbound in Xray
        
        Args:
            inbound_tag: Unique identifier for inbound (e.g., "vless_users")
            port: Port to listen on
            clients: List of client objects with id (UUID), flow, email
            fallbacks: Optional fallback configuration
        
        Returns:
            Response from API
        """
        payload = {
            "inbounds": [
                {
                    "tag": inbound_tag,
                    "port": port,
                    "protocol": "vless",
                    "settings": {
                        "clients": clients,
                        "decryption": "none",
                        "fallbacks": fallbacks or [],
                    },
                    "streamSettings": {
                        "network": "tcp",
                        "tcpSettings": {},
                    },
                }
            ]
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.api_url}/api/inbounds",
                    json=payload,
                    headers=self.base_headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    data = await resp.json()
                    if resp.status != 200:
                        logger.error(f"Failed to create VLESS inbound: {data}")
                        raise RuntimeError(f"Xray API error: {data}")
                    return data
            except asyncio.TimeoutError:
                logger.error("Xray API timeout")
                raise RuntimeError("Xray API timeout")
            except aiohttp.ClientError as e:
                logger.error(f"Xray API connection error: {e}")
                raise RuntimeError(f"Xray API error: {e}")
    
    async def add_client_to_inbound(
        self,
        inbound_tag: str,
        client_id: str,
        email: str,
        flow: str = "",
    ) -> dict:
        """
        Add a single client to existing VLESS inbound
        
        Args:
            inbound_tag: Inbound identifier
            client_id: UUID for the client
            email: Email/identifier for the client
            flow: Flow type (empty for VLESS without xtls, "xtls-rprx-vision" for XTLS)
        
        Returns:
            Response from API
        """
        payload = {
            "clientId": client_id,
            "email": email,
            "flow": flow,
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.api_url}/api/inbounds/{inbound_tag}/clients",
                    json=payload,
                    headers=self.base_headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    data = await resp.json()
                    if resp.status != 200:
                        logger.error(f"Failed to add client: {data}")
                        raise RuntimeError(f"Xray API error: {data}")
                    return data
            except asyncio.TimeoutError:
                logger.error("Xray API timeout")
                raise RuntimeError("Xray API timeout")
            except aiohttp.ClientError as e:
                logger.error(f"Xray API connection error: {e}")
                raise RuntimeError(f"Xray API error: {e}")
    
    async def get_inbound(self, inbound_tag: str) -> dict:
        """Get inbound configuration"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{self.api_url}/api/inbounds/{inbound_tag}",
                    headers=self.base_headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    data = await resp.json()
                    if resp.status != 200:
                        logger.error(f"Failed to get inbound: {data}")
                        raise RuntimeError(f"Xray API error: {data}")
                    return data
            except asyncio.TimeoutError:
                logger.error("Xray API timeout")
                raise RuntimeError("Xray API timeout")
            except aiohttp.ClientError as e:
                logger.error(f"Xray API connection error: {e}")
                raise RuntimeError(f"Xray API error: {e}")
    
    async def remove_client_from_inbound(
        self,
        inbound_tag: str,
        client_id: str,
    ) -> dict:
        """Remove a client from inbound"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.delete(
                    f"{self.api_url}/api/inbounds/{inbound_tag}/clients/{client_id}",
                    headers=self.base_headers,
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    data = await resp.json()
                    if resp.status != 200:
                        logger.error(f"Failed to remove client: {data}")
                        raise RuntimeError(f"Xray API error: {data}")
                    return data
            except asyncio.TimeoutError:
                logger.error("Xray API timeout")
                raise RuntimeError("Xray API timeout")
            except aiohttp.ClientError as e:
                logger.error(f"Xray API connection error: {e}")
                raise RuntimeError(f"Xray API error: {e}")


async def generate_vless_config(
    settings: Settings,
    user_uuid: str,
    user_email: str,
    protocol: str = "vless",
    flow: str = "",
) -> str:
    """
    Generate VLESS configuration string for user
    
    Format: vless://[id]@[address]:[port]?[parameters]#[remarks]
    """
    params = []
    params.append(f"type=tcp")
    if flow:
        params.append(f"flow={flow}")
    params.append("security=none")  # or "tls" if using TLS
    
    params_str = "&".join(params)
    remarks = f"{user_email}"
    
    config = (
        f"vless://{user_uuid}@{settings.vpn_endpoint_host}:"
        f"{settings.vpn_endpoint_port}?{params_str}#{remarks}"
    )
    
    return config


async def generate_vmess_config(
    settings: Settings,
    user_uuid: str,
    user_email: str,
    alter_id: int = 0,
) -> str:
    """
    Generate VMess configuration (JSON format)
    """
    config = {
        "v": "2",
        "ps": user_email,
        "add": settings.vpn_endpoint_host,
        "port": settings.vpn_endpoint_port,
        "id": user_uuid,
        "aid": alter_id,
        "net": "tcp",
        "type": "none",
        "host": "",
        "path": "",
        "tls": "",
        "sni": "",
    }
    
    return json.dumps(config)
