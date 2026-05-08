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

    # SSH / Amnezia server settings (optional)
    ssh_host: str | None = None
    ssh_port: int | None = None
    ssh_user: str | None = None
    ssh_key_path: str | None = None
    ssh_password: str | None = None

    # WireGuard server settings (defaults can be overridden by env)
    wg_endpoint_host: str | None = None
    wg_endpoint_port: int | None = None
    wg_server_public_key: str | None = None
    wg_client_network_prefix: str | None = None
    wg_client_start_octet: int | None = None
    wg_allowed_ips: str | None = None
    wg_dns: str | None = None
    wg_mtu: int | None = None
    wg_interface_name: str | None = None
    wg_docker_container: str | None = None

    # AWG-specific params
    awg_jc: int | None = None
    awg_jmin: int | None = None
    awg_jmax: int | None = None
    awg_s1: int | None = None
    awg_s2: int | None = None
    awg_s3: int | None = None
    awg_s4: int | None = None
    awg_h1: int | None = None
    awg_h2: int | None = None
    awg_h3: int | None = None
    awg_h4: int | None = None
    debug_network: bool = False

    @classmethod
    def from_env(cls) -> "Settings":
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        generator_api_base_url = os.getenv("GENERATOR_API_BASE_URL", "https://valokda-amnezia.vercel.app").strip()

        if not bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

        parsed = urlparse(generator_api_base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise RuntimeError("GENERATOR_API_BASE_URL must be a valid http(s) URL")

        # SSH/WG optional vars
        ssh_host = os.getenv("SSH_HOST")
        ssh_port = int(os.getenv("SSH_PORT", "22")) if os.getenv("SSH_PORT") else None
        ssh_user = os.getenv("SSH_USER")
        ssh_key_path = os.getenv("SSH_KEY_PATH")
        ssh_password = os.getenv("SSH_PASSWORD")

        wg_endpoint_host = os.getenv("WIREGUARD_ENDPOINT_HOST")
        wg_endpoint_port = int(os.getenv("WIREGUARD_ENDPOINT_PORT")) if os.getenv("WIREGUARD_ENDPOINT_PORT") else None
        wg_server_public_key = os.getenv("WIREGUARD_SERVER_PUBLIC_KEY")
        wg_client_network_prefix = os.getenv("WIREGUARD_CLIENT_NETWORK_PREFIX")
        wg_client_start_octet = int(os.getenv("WIREGUARD_CLIENT_START_OCTET")) if os.getenv("WIREGUARD_CLIENT_START_OCTET") else None
        wg_allowed_ips = os.getenv("WIREGUARD_ALLOWED_IPS")
        wg_dns = os.getenv("WIREGUARD_DNS")
        wg_mtu = int(os.getenv("WIREGUARD_MTU")) if os.getenv("WIREGUARD_MTU") else None
        wg_interface_name = os.getenv("WIREGUARD_INTERFACE_NAME")
        wg_docker_container = os.getenv("WIREGUARD_DOCKER_CONTAINER")

        awg_jc = int(os.getenv("WIREGUARD_AWG_JC")) if os.getenv("WIREGUARD_AWG_JC") else None
        awg_jmin = int(os.getenv("WIREGUARD_AWG_JMIN")) if os.getenv("WIREGUARD_AWG_JMIN") else None
        awg_jmax = int(os.getenv("WIREGUARD_AWG_JMAX")) if os.getenv("WIREGUARD_AWG_JMAX") else None
        awg_s1 = int(os.getenv("WIREGUARD_AWG_S1")) if os.getenv("WIREGUARD_AWG_S1") else None
        awg_s2 = int(os.getenv("WIREGUARD_AWG_S2")) if os.getenv("WIREGUARD_AWG_S2") else None
        awg_s3 = int(os.getenv("WIREGUARD_AWG_S3")) if os.getenv("WIREGUARD_AWG_S3") else None
        awg_s4 = int(os.getenv("WIREGUARD_AWG_S4")) if os.getenv("WIREGUARD_AWG_S4") else None
        awg_h1 = int(os.getenv("WIREGUARD_AWG_H1")) if os.getenv("WIREGUARD_AWG_H1") else None
        awg_h2 = int(os.getenv("WIREGUARD_AWG_H2")) if os.getenv("WIREGUARD_AWG_H2") else None
        awg_h3 = int(os.getenv("WIREGUARD_AWG_H3")) if os.getenv("WIREGUARD_AWG_H3") else None
        awg_h4 = int(os.getenv("WIREGUARD_AWG_H4")) if os.getenv("WIREGUARD_AWG_H4") else None
        debug_network = os.getenv("DEBUG_NETWORK", "").lower() in ("1", "true", "yes")

        return cls(
            bot_token=bot_token,
            generator_api_base_url=generator_api_base_url.rstrip("/"),
            ssh_host=ssh_host,
            ssh_port=ssh_port,
            ssh_user=ssh_user,
            ssh_key_path=ssh_key_path,
            ssh_password=ssh_password,
            wg_endpoint_host=wg_endpoint_host,
            wg_endpoint_port=wg_endpoint_port,
            wg_server_public_key=wg_server_public_key,
            wg_client_network_prefix=wg_client_network_prefix,
            wg_client_start_octet=wg_client_start_octet,
            wg_allowed_ips=wg_allowed_ips,
            wg_dns=wg_dns,
            wg_mtu=wg_mtu,
            wg_interface_name=wg_interface_name,
            wg_docker_container=wg_docker_container,
            awg_jc=awg_jc,
            awg_jmin=awg_jmin,
            awg_jmax=awg_jmax,
            awg_s1=awg_s1,
            awg_s2=awg_s2,
            awg_s3=awg_s3,
            awg_s4=awg_s4,
            awg_h1=awg_h1,
            awg_h2=awg_h2,
            awg_h3=awg_h3,
            awg_h4=awg_h4,
            debug_network=debug_network,
        )
