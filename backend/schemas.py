from pydantic import BaseModel, ConfigDict
from typing import Any, Optional


class PeerCreate(BaseModel):
    # Optional name or label for peer
    name: Optional[str] = None


class PeerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    public_key: str
    preshared_key: Optional[str]
    client_ip: Optional[str]
    applied: bool
    masquerade_added: bool
    meta: Optional[Any]


class UserCreate(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    is_active: bool
    is_admin: bool


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class PlanCreate(BaseModel):
    name: str
    price_cents: int
    duration_days: int = 30


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price_cents: int
    duration_days: int


class SubscribeRequest(BaseModel):
    plan_id: int
