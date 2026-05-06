from __future__ import annotations

import asyncio
import base64
import re
from typing import Any

import paramiko

from .config import Settings

from nacl import public


def _generate_keypair() -> tuple[str, str]:
    private_key = public.PrivateKey.generate()
    public_key = private_key.public_key
    priv_b64 = base64.b64encode(private_key.encode()).decode("ascii")
    pub_b64 = base64.b64encode(public_key.encode()).decode("ascii")
    return priv_b64, pub_b64


def _ssh_connect(settings: Settings) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connect_kwargs = {
        "hostname": settings.ssh_host,
        "username": settings.ssh_user,
        "port": settings.ssh_port or 22,
        "timeout": 10,
    }
    if settings.ssh_key_path:
        connect_kwargs["key_filename"] = settings.ssh_key_path
    if settings.ssh_password:
        connect_kwargs["password"] = settings.ssh_password
    client.connect(**connect_kwargs)
    return client


def _run_ssh(cmd: str, client: paramiko.SSHClient) -> str:
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode("utf-8")
    err = stderr.read().decode("utf-8")
    if err and not out:
        raise RuntimeError(f"SSH command error: {err.strip()}")
    return out.strip()


def _find_next_ip(dump_output: str, prefix: str, start_octet: int) -> str:
    used = set()
    for line in dump_output.splitlines():
        # find any x.x.x.Y/32 containing prefix
        m = re.search(rf"({re.escape(prefix)}\.(\d+))/32", line)
        if m:
            used.add(int(m.group(2)))
    octet = start_octet
    while octet < 255:
        if octet not in used:
            return f"{prefix}.{octet}"
        octet += 1
    raise RuntimeError("No available IP in the client range")


async def create_peer(settings: Settings) -> tuple[str, dict[str, Any]]:
    # Runs SSH commands to add peer to Amnezia and returns client config
    if not settings.ssh_host or not settings.ssh_user:
        raise RuntimeError("SSH_HOST and SSH_USER must be set to use remote Amnezia")

    priv, pub = _generate_keypair()

    def _work():
        client = _ssh_connect(settings)
        try:
            container = settings.wg_docker_container or "amnezia-awg"
            iface = settings.wg_interface_name or "wg0"

            # get existing peers dump
            dump_cmd = f"docker exec {container} wg show {iface} dump || true"
            dump = _run_ssh(dump_cmd, client)

            prefix = settings.wg_client_network_prefix or "10.8.1"
            start = settings.wg_client_start_octet or 16
            client_ip = _find_next_ip(dump, prefix, start)

            # add peer
            add_cmd = f"docker exec {container} wg set {iface} peer {base64.b64decode(pub).hex()} allowed-ips {client_ip}/32"
            # The above assumes server accepts raw pubkey in binary hex, but many wg tools expect base64 pubkey.
            # Instead, pass the base64 pubkey directly.
            add_cmd = f"docker exec {container} wg set {iface} peer {pub} allowed-ips {client_ip}/32"
            _run_ssh(add_cmd, client)

            # get server public key if not provided
            server_pub = settings.wg_server_public_key
            if not server_pub:
                try:
                    server_pub = _run_ssh(f"docker exec {container} wg show {iface} public-key", client).strip()
                except Exception:
                    server_pub = None

            endpoint_host = settings.wg_endpoint_host or ""
            endpoint_port = settings.wg_endpoint_port or 0

            # Build config text
            dns = settings.wg_dns or "1.1.1.1,8.8.8.8"
            mtu = settings.wg_mtu or 1280
            keepalive = settings.awg_jc or 25

            conf_lines = [
                "# Compatible with Amnezia and WireGuard",
                "[Interface]",
                f"PrivateKey = {priv}",
                f"Address = {client_ip}/32",
                f"DNS = {dns}",
                f"MTU = {mtu}",
                "",
                "[Peer]",
                f"PublicKey = {server_pub or ''}",
                "PresharedKey = ",
                f"AllowedIPs = {settings.wg_allowed_ips or '0.0.0.0/0'}",
                f"Endpoint = {endpoint_host}:{endpoint_port}",
                f"PersistentKeepalive = {keepalive}",
            ]
            conf_text = "\n".join(conf_lines)
            return conf_text, {"client_ip": client_ip}
        finally:
            client.close()

    return await asyncio.to_thread(_work)
