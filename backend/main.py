import os
import logging
import uuid
from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from datetime import timedelta
from sqlalchemy.orm import Session

from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

from . import database, crud, schemas, auth
from .auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user
from .models import User as _User

app = FastAPI(
    title="Xray VPN Control API",
    description="API for managing Xray VPN subscriptions and user authentication",
    version="2.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("xray_backend")

# Prometheus metrics
REQUEST_COUNT = Counter("xray_requests_total", "Total HTTP requests", ["method", "endpoint"])
USERS_CREATED = Counter("xray_users_created_total", "Number of VPN users created")
SUBSCRIPTIONS = Counter("xray_subscriptions_total", "Number of subscriptions made")


def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.middleware("http")
async def prometheus_middleware(request, call_next):
    try:
        resp = await call_next(request)
        REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
        return resp
    except Exception:
        REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
        raise


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
def health():
    return {"status": "ok", "service": "xray_vpn_api"}


@app.on_event("startup")
async def startup():
    logger.info("Starting Xray VPN API...")
    database.init_db()
    logger.info("Database initialized")
    
    # Create initial admin user if provided via env
    admin_user = os.getenv("ADMIN_USER", "admin")
    admin_pass = os.getenv("ADMIN_PASSWORD", "admin123")
    
    db = database.SessionLocal()
    try:
        existing = db.query(_User).filter(_User.username == admin_user).first()
        if not existing:
            hashed = auth.get_password_hash(admin_pass)
            u = _User(username=admin_user, hashed_password=hashed, is_admin=True, is_active=True)
            db.add(u)
            db.commit()
            logger.info(f"Created admin user: {admin_user}")
    except Exception as e:
        logger.error(f"Error creating admin user: {e}")
    finally:
        db.close()


# ============ AUTH ENDPOINTS ============

@app.post("/auth/register", response_model=schemas.UserOut)
def register(form: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    if db.query(_User).filter(_User.username == form.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed = auth.get_password_hash(form.password)
    user = _User(username=form.username, hashed_password=hashed, is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info(f"New user registered: {form.username}")
    return user


@app.post("/auth/token", response_model=schemas.Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Get JWT token"""
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


# ============ USER ENDPOINTS ============

@app.get("/users/me", response_model=schemas.UserOut)
def get_current_user_info(current_user: _User = Depends(get_current_user)):
    """Get current user info"""
    return current_user


# ============ VPN USER ENDPOINTS ============

@app.post("/vpn/users", response_model=dict)
async def create_vpn_user(
    current_user: _User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new VPN user (config) for current user"""
    try:
        user_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{current_user.id}@vpn"))
        user_email = f"tg_{current_user.id}"
        
        # In real implementation, would add to Xray via Xray API
        # For now, just return config info
        
        USERS_CREATED.inc()
        return {
            "user_id": user_uuid,
            "email": user_email,
            "created_at": "now",
            "status": "active"
        }
    except Exception as exc:
        logger.error(f"Error creating VPN user: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


# ============ PLAN ENDPOINTS ============

def require_admin(current_user=Depends(get_current_user)):
    """Check if user is admin"""
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Admin required")
    return current_user


@app.post("/plans", response_model=schemas.PlanOut)
def create_plan(
    plan: schemas.PlanCreate,
    db: Session = Depends(get_db),
    admin: _User = Depends(require_admin)
):
    """Create a new subscription plan"""
    p = crud.create_plan(db, plan.name, plan.price_cents, plan.duration_days)
    logger.info(f"New plan created: {plan.name}")
    return p


@app.get("/plans", response_model=list[schemas.PlanOut])
def list_plans(db: Session = Depends(get_db)):
    """List all available subscription plans"""
    return crud.list_plans(db)


@app.get("/plans/{plan_id}", response_model=schemas.PlanOut)
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    """Get plan details"""
    p = crud.get_plan(db, plan_id)
    if not p:
        raise HTTPException(status_code=404, detail="Plan not found")
    return p


# ============ SUBSCRIPTION ENDPOINTS ============

@app.post("/subscriptions")
def subscribe_to_plan(
    req: schemas.SubscribeRequest,
    db: Session = Depends(get_db),
    current_user: _User = Depends(get_current_user)
):
    """Subscribe user to a plan"""
    try:
        sub = crud.subscribe_user(db, current_user.id, req.plan_id)
        SUBSCRIPTIONS.inc()
        logger.info(f"User {current_user.id} subscribed to plan {req.plan_id}")
        return {
            "subscription_id": sub.id,
            "status": "active",
            "expires_at": sub.ends_at.isoformat()
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/subscriptions/active", response_model=dict)
def get_active_subscription(
    current_user: _User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's active subscription"""
    sub = crud.get_active_subscription(db, current_user.id)
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription")
    
    from .models import Plan
    plan = db.query(Plan).filter(Plan.id == sub.plan_id).first()
    
    return {
        "subscription_id": sub.id,
        "plan_name": plan.name if plan else "Unknown",
        "plan_id": sub.plan_id,
        "expires_at": sub.ends_at.isoformat(),
        "days_remaining": (sub.ends_at - __import__('datetime').datetime.utcnow()).days
    }


# ============ ADMIN ENDPOINTS ============

@app.get("/admin/stats")
def get_stats(
    db: Session = Depends(get_db),
    admin: _User = Depends(require_admin)
):
    """Get system statistics"""
    from .models import User, Subscription
    
    total_users = db.query(User).count()
    active_subscriptions = db.query(Subscription).filter(Subscription.active == True).count()
    
    return {
        "total_users": total_users,
        "active_subscriptions": active_subscriptions,
        "service": "xray_vpn_api"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000"))
    )
