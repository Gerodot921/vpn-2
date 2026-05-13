import os
import logging
from fastapi import FastAPI, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from sqlalchemy.orm import Session

from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST

from . import database, crud, schemas, auth
from .auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES, get_current_user
from fastapi import Security
from .models import User as _User

app = FastAPI(title="Amnezia VPN Control API")

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("amnezia_backend")

# Prometheus metrics
REQUEST_COUNT = Counter("amnezia_requests_total", "Total HTTP requests", ["method", "endpoint"])
PEERS_CREATED = Counter("amnezia_peers_created_total", "Number of peers created")


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
    return {"status": "ok"}


@app.on_event("startup")
async def startup():
    database.init_db()
    # restore peers from DB into Amnezia
    try:
        db = database.SessionLocal()
        await crud.restore_peers(db)
    finally:
        try:
            db.close()
        except Exception:
            pass

    # create initial admin user if provided via env
    admin_user = os.getenv("ADMIN_USER")
    admin_pass = os.getenv("ADMIN_PASS")
    if admin_user and admin_pass:
        db = database.SessionLocal()
        try:
            from .models import User

            existing = db.query(User).filter(User.username == admin_user).first()
            if not existing:
                hashed = auth.get_password_hash(admin_pass)
                u = User(username=admin_user, hashed_password=hashed, is_admin=True)
                db.add(u)
                db.commit()
        finally:
            db.close()


@app.post("/auth/register", response_model=schemas.UserOut)
def register(form: schemas.UserCreate, db: Session = Depends(get_db)):
    # Simple registration (no email confirmation)
    from .models import User as _User

    if db.query(_User).filter(_User.username == form.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    hashed = auth.get_password_hash(form.password)
    user = _User(username=form.username, hashed_password=hashed)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/peers", response_model=schemas.PeerOut)
async def create_peer_endpoint(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    try:
        peer = await crud.create_peer(db)
        PEERS_CREATED.inc()
        return peer
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/peers", response_model=list[schemas.PeerOut])
def list_peers_endpoint(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return crud.list_peers(db)


def require_admin(current_user=Depends(get_current_user)):
    if not getattr(current_user, "is_admin", False):
        raise HTTPException(status_code=403, detail="Requires admin")
    return current_user


@app.post("/plans", response_model=schemas.PlanOut)
def create_plan_endpoint(plan: schemas.PlanCreate, db: Session = Depends(get_db), admin=Depends(require_admin)):
    p = crud.create_plan(db, plan.name, plan.price_cents, plan.duration_days)
    return p


@app.get("/plans", response_model=list[schemas.PlanOut])
def list_plans_endpoint(db: Session = Depends(get_db)):
    return crud.list_plans(db)


@app.post("/subscribe")
def subscribe_endpoint(req: schemas.SubscribeRequest, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    sub = crud.subscribe_user(db, current_user.id, req.plan_id)
    return {"subscribed": True, "subscription_id": sub.id}


@app.get("/peers/{peer_id}", response_model=schemas.PeerOut)
def get_peer_endpoint(peer_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    p = crud.get_peer(db, peer_id)
    if not p:
        raise HTTPException(status_code=404, detail="Peer not found")
    return p


@app.delete("/peers/{peer_id}")
def delete_peer_endpoint(peer_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    ok = crud.delete_peer(db, peer_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Peer not found")
    return {"deleted": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", "8000")))
