"""Billing plans and payment payload helpers for the Telegram bot."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanOffer:
    plan_id: str
    title: str
    duration_days: int
    price_cents: int
    description: str


DEFAULT_PLANS: tuple[PlanOffer, ...] = (
    PlanOffer(
        plan_id="basic",
        title="Basic",
        duration_days=30,
        price_cents=500,
        description="1 month access",
    ),
    PlanOffer(
        plan_id="pro",
        title="Pro",
        duration_days=90,
        price_cents=1200,
        description="3 months access",
    ),
    PlanOffer(
        plan_id="premium",
        title="Premium",
        duration_days=365,
        price_cents=4000,
        description="12 months access",
    ),
)


def get_plan(plan_id: str) -> PlanOffer | None:
    normalized = (plan_id or "").strip().lower()
    for plan in DEFAULT_PLANS:
        if plan.plan_id == normalized:
            return plan
    return None


def build_invoice_payload(plan_id: str, telegram_user_id: int) -> str:
    return f"purchase:{plan_id}:{telegram_user_id}"


def parse_invoice_payload(payload: str) -> tuple[str, int] | None:
    parts = (payload or "").split(":")
    if len(parts) != 3 or parts[0] != "purchase":
        return None
    try:
        return parts[1], int(parts[2])
    except ValueError:
        return None


def plan_summary_lines() -> list[str]:
    return [f"{plan.title}: {plan.duration_days} days / ${plan.price_cents / 100:.2f}" for plan in DEFAULT_PLANS]
