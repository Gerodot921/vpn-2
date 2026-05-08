from __future__ import annotations

import asyncio
import base64
import re
from typing import Any

import paramiko
import secrets

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
    # Prefer explicit auth method. Disable agent/keys lookup when using password to avoid unexpected key attempts.
    connect_kwargs["allow_agent"] = False
    connect_kwargs["look_for_keys"] = False
    if settings.ssh_key_path:
        connect_kwargs["key_filename"] = settings.ssh_key_path
    if settings.ssh_password:
        connect_kwargs["password"] = settings.ssh_password
    try:
        client.connect(**connect_kwargs)
    except paramiko.AuthenticationException as exc:
        raise RuntimeError("SSH authentication failed. Проверьте SSH_KEY_PATH или SSH_PASSWORD и права доступа.") from exc
    return client


def _run_ssh(cmd: str, client: paramiko.SSHClient) -> str:
    stdin, stdout, stderr = client.exec_command(cmd)
    out = stdout.read().decode("utf-8")
    err = stderr.read().decode("utf-8")
    if err and not out:
        raise RuntimeError(f"SSH command error: {err.strip()}")
    return out.strip()


def _parse_wg_conf(conf_text: str) -> dict[str, str]:
    """Parse simple key = value pairs from wg0.conf Interface section."""
    out: dict[str, str] = {}
    section = None
    for line in conf_text.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('[') and line.endswith(']'):
            section = line[1:-1].strip()
            continue
        if '=' in line and section == 'Interface':
            k, v = line.split('=', 1)
            out[k.strip()] = v.strip()
    return out


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
    # generate preshared key for the peer (base64)
    psk = base64.b64encode(secrets.token_bytes(32)).decode("ascii")

    def _work():
        client = _ssh_connect(settings)
        try:
            container = settings.wg_docker_container or "amnezia-awg"
            iface = settings.wg_interface_name or "wg0"

            # try read wg0.conf inside container to extract server AWG params
            conf_text = None
            try:
                conf_text = _run_ssh(f"docker exec {container} cat /opt/amnezia/awg/wg0.conf", client)
            except Exception:
                conf_text = None

            conf_values: dict[str, str] = {}
            if conf_text:
                try:
                    conf_values = _parse_wg_conf(conf_text)
                except Exception:
                    conf_values = {}

            # get existing peers dump
            dump_cmd = f"docker exec {container} wg show {iface} dump || true"
            dump = _run_ssh(dump_cmd, client)

            # derive client address prefix and start octet
            prefix = settings.wg_client_network_prefix or None
            start = settings.wg_client_start_octet or 16
            if not prefix and conf_values.get('Address'):
                # Address might be like 10.8.1.0/24 or 10.8.1.125/32
                addr = conf_values.get('Address').split(',')[0].strip()
                # take first ipv4 and convert to prefix
                m = re.search(r"(\d+\.\d+\.\d+)\.\d+", addr)
                if m:
                    prefix = m.group(1)
            if not prefix:
                prefix = '10.8.1'
            client_ip = _find_next_ip(dump, prefix, start)

            # add peer and set preshared key inside the container safely
            # write PSK to a temporary file with restrictive permissions, apply, then remove
            set_cmd = (
                f"docker exec {container} sh -c \"umask 077; echo '{psk}' > /tmp/peer_psk; chmod 600 /tmp/peer_psk; "
                f"wg set {iface} peer '{pub}' preshared-key /tmp/peer_psk allowed-ips {client_ip}/32; rm -f /tmp/peer_psk\""
            )
            _run_ssh(set_cmd, client)

            # get server public key if not provided
            server_pub = settings.wg_server_public_key
            if not server_pub:
                try:
                    server_pub = _run_ssh(f"docker exec {container} wg show {iface} public-key", client).strip()
                except Exception:
                    server_pub = None

            # Determine endpoint host/port
            endpoint_host = settings.wg_endpoint_host or conf_values.get('ListenPort') and settings.wg_endpoint_host or settings.ssh_host or ''
            # prefer explicit env port, else use ListenPort from conf
            endpoint_port = settings.wg_endpoint_port or None
            if not endpoint_port and conf_values.get('ListenPort'):
                try:
                    endpoint_port = int(conf_values.get('ListenPort'))
                except Exception:
                    endpoint_port = None
            if not endpoint_port:
                endpoint_port = 0

            # Build config text (include AWG/legacy obfuscation fields to be Amnezia-compatible)
            dns = settings.wg_dns or conf_values.get('DNS') or "1.1.1.1,8.8.8.8"
            mtu = settings.wg_mtu or (int(conf_values.get('MTU')) if conf_values.get('MTU') else 1280)

            # AWG params: prefer values from server conf, then .env, then safe defaults
            jc = int(conf_values.get('Jc')) if conf_values.get('Jc') else (settings.awg_jc or 6)
            jmin = int(conf_values.get('Jmin')) if conf_values.get('Jmin') else (settings.awg_jmin or 10)
            jmax = int(conf_values.get('Jmax')) if conf_values.get('Jmax') else (settings.awg_jmax or 50)
            s1 = int(conf_values.get('S1')) if conf_values.get('S1') else (settings.awg_s1 if settings.awg_s1 is not None else 0)
            s2 = int(conf_values.get('S2')) if conf_values.get('S2') else (settings.awg_s2 if settings.awg_s2 is not None else 0)
            s3 = int(conf_values.get('S3')) if conf_values.get('S3') else (settings.awg_s3 if settings.awg_s3 is not None else 16)
            s4 = int(conf_values.get('S4')) if conf_values.get('S4') else (settings.awg_s4 if settings.awg_s4 is not None else 0)
            h1 = conf_values.get('H1') or settings.awg_h1 or '1'
            h2 = conf_values.get('H2') or settings.awg_h2 or '2'
            h3 = conf_values.get('H3') or settings.awg_h3 or '3'
            h4 = conf_values.get('H4') or settings.awg_h4 or '4'

            conf_lines = [
                "# Compatible with Amnezia and WireGuard",
                "[Interface]",
                f"PrivateKey = {priv}",
                f"Address = {client_ip}/32",
                f"DNS = {dns}",
                f"MTU = {mtu}",
                f"S1 = {s1}",
                f"S2 = {s2}",
                f"Jc = {jc}",
                f"Jmin = {jmin}",
                f"Jmax = {jmax}",
                f"H1 = {h1}",
                f"H2 = {h2}",
                f"H3 = {h3}",
                f"H4 = {h4}",
                "",
                "[Peer]",
                f"PublicKey = {server_pub or ''}",
                f"PresharedKey = {psk}",
                f"AllowedIPs = {settings.wg_allowed_ips or '0.0.0.0/0'}",
                f"Endpoint = {endpoint_host}:{endpoint_port}",
                f"PersistentKeepalive = {settings.awg_jc or 25}",
            ]
            conf_text = "\n".join(conf_lines)
            return conf_text, {"client_ip": client_ip, "preshared_key": psk}
        finally:
            client.close()

    return await asyncio.to_thread(_work)
