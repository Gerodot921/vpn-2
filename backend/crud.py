import os
from typing import Any
from sqlalchemy.orm import Session

from . import models
from datetime import datetime, timedelta
from app.config import Settings
from app.amnezia_ssh import create_peer as amnezia_create_peer, apply_peer as amnezia_apply_peer


def _build_settings_from_env() -> Settings:
    # Construct Settings dataclass used by app.amnezia_ssh.create_peer
    return Settings(
        bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "backend"),
        generator_api_base_url=os.getenv("GENERATOR_API_BASE_URL", ""),
        ssh_host=os.getenv("SSH_HOST"),
        ssh_port=int(os.getenv("SSH_PORT")) if os.getenv("SSH_PORT") else None,
        ssh_user=os.getenv("SSH_USER"),
        ssh_key_path=os.getenv("SSH_KEY_PATH"),
        ssh_password=os.getenv("SSH_PASSWORD"),
        wg_endpoint_host=os.getenv("WIREGUARD_ENDPOINT_HOST"),
        wg_endpoint_port=int(os.getenv("WIREGUARD_ENDPOINT_PORT")) if os.getenv("WIREGUARD_ENDPOINT_PORT") else None,
        wg_server_public_key=os.getenv("WIREGUARD_SERVER_PUBLIC_KEY"),
        wg_client_network_prefix=os.getenv("WIREGUARD_CLIENT_NETWORK_PREFIX"),
        wg_client_start_octet=int(os.getenv("WIREGUARD_CLIENT_START_OCTET")) if os.getenv("WIREGUARD_CLIENT_START_OCTET") else None,
        wg_allowed_ips=os.getenv("WIREGUARD_ALLOWED_IPS"),
        wg_dns=os.getenv("WIREGUARD_DNS"),
        wg_mtu=int(os.getenv("WIREGUARD_MTU")) if os.getenv("WIREGUARD_MTU") else None,
        wg_interface_name=os.getenv("WIREGUARD_INTERFACE_NAME"),
        wg_docker_container=os.getenv("WIREGUARD_DOCKER_CONTAINER"),
        awg_jc=int(os.getenv("WIREGUARD_AWG_JC")) if os.getenv("WIREGUARD_AWG_JC") else None,
        awg_jmin=int(os.getenv("WIREGUARD_AWG_JMIN")) if os.getenv("WIREGUARD_AWG_JMIN") else None,
        awg_jmax=int(os.getenv("WIREGUARD_AWG_JMAX")) if os.getenv("WIREGUARD_AWG_JMAX") else None,
        awg_s1=int(os.getenv("WIREGUARD_AWG_S1")) if os.getenv("WIREGUARD_AWG_S1") else None,
        awg_s2=int(os.getenv("WIREGUARD_AWG_S2")) if os.getenv("WIREGUARD_AWG_S2") else None,
        awg_s3=int(os.getenv("WIREGUARD_AWG_S3")) if os.getenv("WIREGUARD_AWG_S3") else None,
        awg_s4=int(os.getenv("WIREGUARD_AWG_S4")) if os.getenv("WIREGUARD_AWG_S4") else None,
        awg_h1=os.getenv("WIREGUARD_AWG_H1"),
        awg_h2=os.getenv("WIREGUARD_AWG_H2"),
        awg_h3=os.getenv("WIREGUARD_AWG_H3"),
        awg_h4=os.getenv("WIREGUARD_AWG_H4"),
        debug_network=os.getenv("DEBUG_NETWORK", "").lower() in ("1", "true", "yes"),
    )


async def create_peer(db: Session) -> models.Peer:
    settings = _build_settings_from_env()
    # Call amnezia async create_peer
    conf_text, meta = await amnezia_create_peer(settings)
    peer = models.Peer(
        public_key=meta.get("public_key") or "",
        preshared_key=meta.get("preshared_key"),
        client_ip=meta.get("client_ip"),
        conf_text=conf_text,
        applied=meta.get("applied", False),
        masquerade_added=meta.get("masquerade_added", False),
        meta=meta,
    )
    db.add(peer)
    db.commit()
    db.refresh(peer)
    return peer


def list_peers(db: Session):
    return db.query(models.Peer).order_by(models.Peer.id.desc()).all()


def get_peer(db: Session, peer_id: int):
    return db.query(models.Peer).filter(models.Peer.id == peer_id).first()


def delete_peer(db: Session, peer_id: int) -> bool:
    p = get_peer(db, peer_id)
    if not p:
        return False
    db.delete(p)
    db.commit()
    return True


async def restore_peers(db: Session) -> None:
    """Restore peers from DB into Amnezia on startup.
    Applies peers that have `applied==False` but have stored keys in meta.
    """
    settings = _build_settings_from_env()
    peers = db.query(models.Peer).filter(models.Peer.applied == False).all()
    for p in peers:
        meta = p.meta or {}
        pub = meta.get("public_key") or p.public_key
        psk = meta.get("preshared_key") or p.preshared_key
        cip = meta.get("client_ip") or p.client_ip
        if not (pub and psk and cip):
            continue
        try:
            res = await amnezia_apply_peer(settings, pub, psk, cip)
            p.applied = res.get("applied", True)
            p.masquerade_added = res.get("masquerade_added", p.masquerade_added)
            db.add(p)
            db.commit()
        except Exception:
            continue


def create_plan(db: Session, name: str, price_cents: int, duration_days: int) -> models.Plan:
    plan = models.Plan(name=name, price_cents=price_cents, duration_days=duration_days)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def list_plans(db: Session) -> list[models.Plan]:
    return db.query(models.Plan).order_by(models.Plan.id.asc()).all()


def subscribe_user(db: Session, user_id: int, plan_id: int) -> models.Subscription:
    # Simple subscribe: create subscription and set ends_at
    plan = db.query(models.Plan).filter(models.Plan.id == plan_id).first()
    if not plan:
        raise RuntimeError("Plan not found")
    starts = datetime.utcnow()
    ends = starts + timedelta(days=plan.duration_days)
    sub = models.Subscription(user_id=user_id, plan_id=plan.id, active=True, starts_at=starts, ends_at=ends)
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def get_active_subscription(db: Session, user_id: int):
    now = datetime.utcnow()
    return db.query(models.Subscription).filter(models.Subscription.user_id == user_id, models.Subscription.active == True, models.Subscription.ends_at > now).first()
