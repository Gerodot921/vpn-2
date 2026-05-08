from __future__ import annotations

from dataclasses import dataclass
import base64
import json
from typing import Any
from urllib.parse import urlencode

import aiohttp


@dataclass(frozen=True)
class GenerationRequest:
    mode: str
    template: str | None = None
    presets: list[str] | None = None
    dns: str | None = None
    peer_endpoint: str | None = None
    keepalive: int | None = None
    i1: str | None = None
    i1_ref: str | None = None
    plain_address: bool = False
    router: bool = False
    cps: str | None = None
    server_public_key: str | None = None


class GeneratorClient:
    def __init__(self, base_url: str, session: aiohttp.ClientSession) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = session

    async def generate(self, request: GenerationRequest) -> tuple[str, dict[str, Any]]:
        payload: dict[str, Any] = {
            "mode": request.mode,
        }
        if request.template:
            payload["template"] = request.template
        if request.presets:
            payload["presets"] = request.presets
        if request.dns:
            payload["dns"] = request.dns
        if request.peer_endpoint:
            payload["peerEndpoint"] = request.peer_endpoint
        if request.keepalive is not None:
            payload["persistentKeepalive"] = request.keepalive
        if request.i1 is not None:
            payload["i1"] = request.i1
        if request.i1_ref:
            payload["i1Ref"] = request.i1_ref
        if request.plain_address:
            payload["plainAddress"] = True
        if request.router:
            payload["router"] = True
        if request.cps:
            payload["cps"] = request.cps

        use_post = request.i1 is not None or len(json.dumps(payload, ensure_ascii=False)) > 1800

        if use_post:
            async with self._session.post(f"{self._base_url}/api/warp", json=payload, timeout=aiohttp.ClientTimeout(total=60)) as response:
                data = await response.json(content_type=None)
        else:
            query = urlencode(self._flatten_query(payload), doseq=True)
            url = f"{self._base_url}/api/warp?{query}" if query else f"{self._base_url}/api/warp"
            async with self._session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                data = await response.json(content_type=None)

        if not isinstance(data, dict) or not data.get("success"):
            message = "Unknown generator error"
            if isinstance(data, dict):
                message = str(data.get("message") or message)
            raise RuntimeError(message)

        content = str(data.get("content") or "")
        if not content:
            raise RuntimeError("Generator returned empty content")

        try:
            conf_text = base64.b64decode(content).decode("utf-8")
        except Exception as exc:  # pragma: no cover - defensive decoding guard
            raise RuntimeError("Failed to decode generator response") from exc

        return conf_text, data

    @staticmethod
    def _flatten_query(payload: dict[str, Any]) -> dict[str, Any]:
        query: dict[str, Any] = {}
        for key, value in payload.items():
            if value is None:
                continue
            if isinstance(value, list):
                query[key] = ",".join(str(item) for item in value)
            elif isinstance(value, bool):
                query[key] = "true" if value else "false"
            else:
                query[key] = value
        return query
