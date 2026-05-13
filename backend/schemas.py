from pydantic import BaseModel
from typing import Any, Optional


class PeerCreate(BaseModel):
    # Optional name or label for peer
    name: Optional[str] = None


class PeerOut(BaseModel):
    id: int
    public_key: str
    preshared_key: Optional[str]
    client_ip: Optional[str]
    applied: bool
    masquerade_added: bool
    meta: Optional[Any]

    class Config:
        orm_mode = True


class UserCreate(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    is_active: bool
    is_admin: bool

    class Config:
        orm_mode = True


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
    id: int
    name: str
    price_cents: int
    duration_days: int

    class Config:
        orm_mode = True


class SubscribeRequest(BaseModel):
    plan_id: int
