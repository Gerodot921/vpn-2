"""
CRUD operations for Xray VPN API
"""

import os
from typing import Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from . import models


# ============ PLAN OPERATIONS ============

def create_plan(db: Session, name: str, price_cents: int, duration_days: int) -> models.Plan:
    """Create a new subscription plan"""
    plan = models.Plan(
        name=name,
        price_cents=price_cents,
        duration_days=duration_days,
        created_at=datetime.utcnow()
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def list_plans(db: Session) -> list[models.Plan]:
    """List all available plans"""
    return db.query(models.Plan).order_by(models.Plan.id.asc()).all()


def get_plan(db: Session, plan_id: int) -> Optional[models.Plan]:
    """Get a specific plan by ID"""
    return db.query(models.Plan).filter(models.Plan.id == plan_id).first()


# ============ SUBSCRIPTION OPERATIONS ============

def subscribe_user(db: Session, user_id: int, plan_id: int) -> models.Subscription:
    """Subscribe a user to a plan"""
    plan = get_plan(db, plan_id)
    if not plan:
        raise ValueError("Plan not found")
    
    # Deactivate any existing active subscription
    db.query(models.Subscription).filter(
        models.Subscription.user_id == user_id,
        models.Subscription.active == True
    ).update({models.Subscription.active: False})
    
    starts = datetime.utcnow()
    ends = starts + timedelta(days=plan.duration_days)
    
    sub = models.Subscription(
        user_id=user_id,
        plan_id=plan.id,
        active=True,
        starts_at=starts,
        ends_at=ends,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def get_active_subscription(db: Session, user_id: int) -> Optional[models.Subscription]:
    """Get user's currently active subscription"""
    now = datetime.utcnow()
    return db.query(models.Subscription).filter(
        models.Subscription.user_id == user_id,
        models.Subscription.active == True,
        models.Subscription.ends_at > now
    ).first()


def expire_old_subscriptions(db: Session) -> int:
    """Mark expired subscriptions as inactive (can be called periodically)"""
    now = datetime.utcnow()
    result = db.query(models.Subscription).filter(
        models.Subscription.active == True,
        models.Subscription.ends_at <= now
    ).update({models.Subscription.active: False})
    db.commit()
    return result

