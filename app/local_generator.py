from __future__ import annotations

from typing import Any
import base64
import json
import secrets

from nacl import public, encoding

from .generator_client import GenerationRequest


def _generate_keypair() -> tuple[str, str]:
    private_key = public.PrivateKey.generate()
    public_key = private_key.public_key
    priv_b64 = base64.b64encode(private_key.encode()).decode("ascii")
    pub_b64 = base64.b64encode(public_key.encode()).decode("ascii")
    return priv_b64, pub_b64


def _generate_psk() -> str:
    raw = secrets.token_bytes(32)
    return base64.b64encode(raw).decode("ascii")


class LocalGenerator:
    async def generate(self, request: GenerationRequest) -> tuple[str, dict[str, Any]]:
        # Simple local generator producing a WireGuard-like config compatible with Amnezia
        priv, pub = _generate_keypair()
        psk = _generate_psk()

        # Format addresses and defaults
        address = request.peer_endpoint or "10.8.1.125/32"
        dns = request.dns or "1.1.1.1,8.8.8.8"
        keepalive = request.keepalive or 25

        conf_lines = [
            "#",
            "# Compatible with Amnezia and WireGuard",
            "[Interface]",
            f"PrivateKey = {priv}",
            f"Address = {address}",
            f"DNS = {dns}",
            "MTU = 1280",
            "S1 = 38",
            "S2 = 108",
            "Jc = 3",
            "Jmin = 10",
            "Jmax = 50",
            "H1 = 1240115562",
            "H2 = 2066276037",
            "H3 = 723255589",
            "H4 = 763917897",
            "",
            "[Peer]",
            f"PublicKey = {pub}",
            f"PresharedKey = {psk}",
            "AllowedIPs = 0.0.0.0/0",
            "Endpoint = 82.25.185.181:49983",
            f"PersistentKeepalive = {keepalive}",
        ]

        conf_text = "\n".join(conf_lines)
        meta = {"generated": True, "preshared_key": psk}
        return conf_text, meta
