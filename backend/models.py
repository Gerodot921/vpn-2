from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.dialects.sqlite import JSON as SQLITE_JSON
from .database import Base


class Peer(Base):
    __tablename__ = "peers"
    id = Column(Integer, primary_key=True, index=True)
    public_key = Column(String, nullable=False)
    preshared_key = Column(String, nullable=True)
    client_ip = Column(String, nullable=True)
    conf_text = Column(String, nullable=True)
    applied = Column(Boolean, default=False)
    masquerade_added = Column(Boolean, default=False)
    meta = Column(SQLITE_JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Plan(Base):
    __tablename__ = "plans"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price_cents = Column(Integer, nullable=False, default=0)
    duration_days = Column(Integer, nullable=False, default=30)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    plan_id = Column(Integer, nullable=False)
    active = Column(Boolean, default=True)
    starts_at = Column(DateTime(timezone=True), server_default=func.now())
    ends_at = Column(DateTime(timezone=True), nullable=True)
