from __future__ import annotations

from typing import Any
import base64
import json

from nacl import public, encoding

from .generator_client import GenerationRequest


def _generate_keypair() -> tuple[str, str]:
    private_key = public.PrivateKey.generate()
    public_key = private_key.public_key
    priv_b64 = base64.b64encode(private_key.encode()).decode("ascii")
    pub_b64 = base64.b64encode(public_key.encode()).decode("ascii")
    return priv_b64, pub_b64


class LocalGenerator:
    async def generate(self, request: GenerationRequest) -> tuple[str, dict[str, Any]]:
        # Simple local generator producing a WireGuard-like config compatible with Amnezia
        priv, pub = _generate_keypair()

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
            "Jc = 6",
            "Jmin = 10",
            "Jmax = 50",
            "S1 = 128",
            "S2 = 76",
            "S3 = 16",
            "S4 = 10",
            "H1 = 161633421-978891746",
            "H2 = 1580984436-185454594",
            "H3 = 2042084841-2112482583",
            "H4 = 2137803850-2140481769",
            "",
            "[Peer]",
            f"PublicKey = {pub}",
            "PresharedKey = ",
            "AllowedIPs = 0.0.0.0/0",
            "Endpoint = 82.25.185.181:49983",
            f"PersistentKeepalive = {keepalive}",
        ]

        conf_text = "\n".join(conf_lines)
        meta = {"generated": True}
        return conf_text, meta
