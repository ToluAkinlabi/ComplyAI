import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select  # type: ignore
from sqlalchemy.orm import Session  # type: ignore

from database.models import Organization, OrganizationMembership, User
from database.session import SessionLocal, ensure_database_ready
from scripts.prod_settings import settings

# Simulated user store (in-memory fallback only; replace with database-backed identity for SaaS)
DEFAULT_ADMIN_EMAIL = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@complyai.io")
DEFAULT_ADMIN_HASH = os.getenv(
    "DEFAULT_ADMIN_PASSWORD_HASH",
    "$2b$12$8J9SWzSn4l3YeRsSV7lXKuihDSYaQF1HAdgbJsgrQ4LKMg/YQK8ui"
)

users_db = {
    DEFAULT_ADMIN_EMAIL: {
        "email": DEFAULT_ADMIN_EMAIL,
        "hashed_password": DEFAULT_ADMIN_HASH,
        "role": "admin"
    }
}

# Password encryption
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def _db_auth_enabled() -> bool:
    return os.getenv("USE_DB_AUTH", "true").lower() != "false"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "complyai"

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def _build_user_claims(email: str, role: str, org_id: Optional[int], user_id: Optional[int]) -> Dict[str, Any]:
    return {
        "email": email,
        "role": role,
        "org_id": org_id,
        "user_id": user_id,
    }


def _to_optional_int(value: Any) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _resolve_user_claims_from_db(db: Session, email: str) -> Optional[Dict[str, Any]]:
    stmt = (
        select(User, OrganizationMembership)
        .join(OrganizationMembership, OrganizationMembership.user_id == User.id, isouter=True)
        .where(User.email == email, User.is_active.is_(True))
        .order_by(OrganizationMembership.id.asc())
    )
    result = db.execute(stmt).first()
    if result is None:
        return None

    user, membership = result

    role = "user"
    org_id = None
    if membership is not None and membership.is_active:
        role = membership.role or "member"
        org_id = membership.organization_id

    return _build_user_claims(email=user.email, role=role, org_id=org_id, user_id=user.id)


def _ensure_bootstrap_admin(db: Session) -> None:
    default_org_name = os.getenv("DEFAULT_ORG_NAME", "ComplyAI")
    default_org_slug = os.getenv("DEFAULT_ORG_SLUG", _slugify(default_org_name))

    org = db.execute(select(Organization).where(Organization.slug == default_org_slug)).scalar_one_or_none()
    if org is None:
        org = Organization(name=default_org_name, slug=default_org_slug)
        db.add(org)
        db.flush()

    user = db.execute(select(User).where(User.email == DEFAULT_ADMIN_EMAIL)).scalar_one_or_none()
    if user is None:
        user = User(
            email=DEFAULT_ADMIN_EMAIL,
            full_name="Bootstrap Admin",
            hashed_password=DEFAULT_ADMIN_HASH,
            is_active=True,
        )
        db.add(user)
        db.flush()

    membership = db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == org.id,
            OrganizationMembership.user_id == user.id,
        )
    ).scalar_one_or_none()
    if membership is None:
        membership = OrganizationMembership(
            organization_id=org.id,
            user_id=user.id,
            role="admin",
            is_active=True,
        )
        db.add(membership)


def init_auth_storage() -> None:
    """Initialize auth storage and seed bootstrap admin identity for local setup."""
    if not _db_auth_enabled():
        return

    ensure_database_ready()
    with SessionLocal() as db:
        _ensure_bootstrap_admin(db)
        db.commit()


def get_user_claims(email: str) -> Optional[Dict[str, Any]]:
    if _db_auth_enabled():
        with SessionLocal() as db:
            claims = _resolve_user_claims_from_db(db, email)
        if claims:
            return claims

    user = users_db.get(email)
    if not user:
        return None

    return _build_user_claims(
        email=user["email"],
        role=user.get("role", "user"),
        org_id=_to_optional_int(user.get("org_id")),
        user_id=_to_optional_int(user.get("user_id")),
    )


def authenticate_user(email: str, plain_password: str) -> Optional[Dict[str, Any]]:
    if _db_auth_enabled():
        with SessionLocal() as db:
            db_user = db.execute(select(User).where(User.email == email, User.is_active.is_(True))).scalar_one_or_none()
            if db_user and verify_password(plain_password, db_user.hashed_password):
                return _resolve_user_claims_from_db(db, email)

    user = users_db.get(email)
    if user and verify_password(plain_password, user["hashed_password"]):
        return _build_user_claims(
            email=user["email"],
            role=user.get("role", "user"),
            org_id=_to_optional_int(user.get("org_id")),
            user_id=_to_optional_int(user.get("user_id")),
        )
    return None

def create_access_token(data: dict, expires_delta: timedelta = timedelta(hours=2)):
    to_encode = data.copy()
    to_encode["exp"] = datetime.utcnow() + expires_delta
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


def _extract_bearer_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    return auth_header.split(" ", 1)[1].strip()

async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    user_email = payload.get("sub")
    if user_email is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user = get_user_claims(user_email)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return user


def require_authenticated_user_if_enabled(request: Request):
    """Enforce auth only when REQUIRE_AUTH=true."""
    if os.getenv("REQUIRE_AUTH", "false").lower() != "true":
        return None

    token = _extract_bearer_token(request)
    payload = decode_access_token(token)
    user_email = payload.get("sub")
    if user_email is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user = get_user_claims(user_email)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return user

def admin_required(user=Depends(get_current_user)):
    if user["role"] not in {"admin", "owner"}:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
