import os
import re
import secrets
import hashlib
from datetime import datetime, timedelta
from threading import Lock
from typing import Any, Dict, Optional, Tuple, cast

from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select  # type: ignore
from sqlalchemy.orm import Session  # type: ignore

from database.models import Organization, OrganizationMembership, RefreshToken, User, UserInvite
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

_login_failures: Dict[str, Dict[str, Any]] = {}
_login_failures_lock = Lock()

MAX_LOGIN_ATTEMPTS = max(1, int(os.getenv("LOGIN_MAX_ATTEMPTS", "5")))
LOGIN_LOCKOUT_MINUTES = max(1, int(os.getenv("LOGIN_LOCKOUT_MINUTES", "15")))

INVITE_ALLOWED_ROLES = {"admin", "analyst", "member", "viewer"}
REPORT_WRITE_ROLES = {"owner", "admin", "analyst", "member"}
REPORT_DELETE_ROLES = {"owner", "admin"}

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


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


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


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def assert_login_not_locked(email: str) -> None:
    normalized_email = _normalize_email(email)
    now = datetime.utcnow()
    with _login_failures_lock:
        state = _login_failures.get(normalized_email)
        if not state:
            return
        locked_until = state.get("locked_until")
        if isinstance(locked_until, datetime) and locked_until > now:
            raise HTTPException(status_code=423, detail="Account temporarily locked due to repeated failed logins")
        if isinstance(locked_until, datetime) and locked_until <= now:
            _login_failures.pop(normalized_email, None)


def register_login_failure(email: str) -> None:
    normalized_email = _normalize_email(email)
    now = datetime.utcnow()
    with _login_failures_lock:
        state = _login_failures.get(normalized_email) or {"count": 0, "locked_until": None}
        count = int(state.get("count", 0)) + 1
        locked_until = state.get("locked_until")
        if count >= MAX_LOGIN_ATTEMPTS:
            locked_until = now + timedelta(minutes=LOGIN_LOCKOUT_MINUTES)
            count = 0
        _login_failures[normalized_email] = {"count": count, "locked_until": locked_until}


def clear_login_failures(email: str) -> None:
    normalized_email = _normalize_email(email)
    with _login_failures_lock:
        _login_failures.pop(normalized_email, None)


def require_roles(user: Optional[Dict[str, Any]], allowed_roles: set[str], detail: str = "Insufficient permissions") -> None:
    if user is None:
        return
    role = str(user.get("role") or "user").lower()
    if role not in allowed_roles:
        raise HTTPException(status_code=403, detail=detail)


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
    email = _normalize_email(email)
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
    email = _normalize_email(email)
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


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_refresh_token(*, user_id: int, expires_delta: timedelta = timedelta(days=30)) -> str:
    raw_token = secrets.token_urlsafe(48)
    token_hash = _hash_token(raw_token)
    expires_at = datetime.utcnow() + expires_delta

    with SessionLocal() as db:
        record = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked_at=None,
        )
        db.add(record)
        db.commit()

    return raw_token


def refresh_access_token(refresh_token: str) -> Tuple[str, str]:
    token_hash = _hash_token(refresh_token)

    with SessionLocal() as db:
        token_record = cast(Any, db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        ).scalar_one_or_none())

        if token_record is None or token_record.revoked_at is not None or token_record.expires_at <= datetime.utcnow():
            raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

        user = cast(Any, db.execute(select(User).where(User.id == token_record.user_id, User.is_active.is_(True))).scalar_one_or_none())
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token user")

        claims = _resolve_user_claims_from_db(db, str(user.email))
        if claims is None:
            raise HTTPException(status_code=401, detail="Could not resolve user claims")

        token_record.revoked_at = datetime.utcnow()
        db.commit()

    access_token = create_access_token(
        data={
            "sub": claims["email"],
            "role": claims.get("role", "user"),
            "org_id": claims.get("org_id"),
            "user_id": claims.get("user_id"),
        }
    )
    new_refresh_token = create_refresh_token(user_id=int(claims["user_id"]))
    return access_token, new_refresh_token


def revoke_refresh_token(refresh_token: str) -> None:
    token_hash = _hash_token(refresh_token)
    with SessionLocal() as db:
        token_record = cast(Any, db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        ).scalar_one_or_none())
        if token_record is None or token_record.revoked_at is not None:
            return
        token_record.revoked_at = datetime.utcnow()
        db.commit()


def create_user_invite(*, actor: Dict[str, Any], email: str, role: str = "member", ttl_hours: int = 72) -> str:
    org_id = _to_optional_int(actor.get("org_id"))
    invited_by_user_id = _to_optional_int(actor.get("user_id"))
    if org_id is None:
        raise HTTPException(status_code=400, detail="Missing organization context")

    normalized_email = email.strip().lower()
    normalized_role = role.strip().lower()
    if not normalized_email:
        raise HTTPException(status_code=400, detail="Invite email is required")
    if normalized_role not in INVITE_ALLOWED_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid invite role. Allowed roles: {', '.join(sorted(INVITE_ALLOWED_ROLES))}",
        )

    existing_user = None
    with SessionLocal() as db:
        existing_user = db.execute(select(User).where(User.email == normalized_email)).scalar_one_or_none()
        if existing_user is not None:
            membership = db.execute(
                select(OrganizationMembership).where(
                    OrganizationMembership.organization_id == org_id,
                    OrganizationMembership.user_id == existing_user.id,
                )
            ).scalar_one_or_none()
            if membership is not None:
                raise HTTPException(status_code=400, detail="User already belongs to this organization")

        raw_token = secrets.token_urlsafe(36)
        token_hash = _hash_token(raw_token)
        invite = UserInvite(
            organization_id=org_id,
            email=normalized_email,
            role=normalized_role,
            token_hash=token_hash,
            invited_by_user_id=invited_by_user_id,
            expires_at=datetime.utcnow() + timedelta(hours=ttl_hours),
            accepted_at=None,
        )
        db.add(invite)
        db.commit()

    return raw_token


def list_user_invites(*, actor: Dict[str, Any]) -> list:
    org_id = _to_optional_int(actor.get("org_id"))
    if org_id is None:
        raise HTTPException(status_code=400, detail="Missing organization context")

    with SessionLocal() as db:
        org = cast(Any, db.execute(select(Organization).where(Organization.id == org_id)).scalar_one_or_none())
        org_name = org.name if org else "Unknown"

        rows = db.execute(
            select(UserInvite)
            .where(UserInvite.organization_id == org_id)
            .order_by(UserInvite.created_at.desc())
        ).scalars().all()

        return [
            {
                "id": r.id,
                "email": r.email,
                "role": r.role,
                "expires_at": r.expires_at.isoformat(),
                "accepted_at": r.accepted_at.isoformat() if r.accepted_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "organization_name": org_name,
                "is_pending": r.accepted_at is None and r.expires_at > datetime.utcnow(),
            }
            for r in rows
        ]


def preview_invite_token(*, invite_token: str) -> Dict[str, Any]:
    token_hash = _hash_token(invite_token)

    with SessionLocal() as db:
        invite = cast(Any, db.execute(select(UserInvite).where(UserInvite.token_hash == token_hash)).scalar_one_or_none())
        if invite is None:
            raise HTTPException(status_code=404, detail="Invite not found")
        if invite.accepted_at is not None:
            raise HTTPException(status_code=400, detail="This invite has already been accepted")
        if invite.expires_at <= datetime.utcnow():
            raise HTTPException(status_code=400, detail="This invite has expired")

        org = cast(Any, db.execute(select(Organization).where(Organization.id == invite.organization_id)).scalar_one_or_none())
        org_name = org.name if org else "Unknown"

        return {
            "email": str(invite.email),
            "role": str(invite.role),
            "organization_name": org_name,
            "expires_at": invite.expires_at.isoformat(),
        }


def accept_user_invite(*, invite_token: str, full_name: str, password: str) -> Dict[str, Any]:
    token_hash = _hash_token(invite_token)
    now = datetime.utcnow()

    with SessionLocal() as db:
        invite = cast(Any, db.execute(select(UserInvite).where(UserInvite.token_hash == token_hash)).scalar_one_or_none())
        if invite is None or invite.accepted_at is not None or invite.expires_at <= now:
            raise HTTPException(status_code=400, detail="Invalid or expired invite token")

        user = cast(Any, db.execute(select(User).where(User.email == invite.email)).scalar_one_or_none())
        if user is None:
            user = User(
                email=invite.email,
                full_name=full_name.strip() or None,
                hashed_password=hash_password(password),
                is_active=True,
            )
            db.add(user)
            db.flush()
        else:
            user.hashed_password = hash_password(password)
            if full_name.strip():
                user.full_name = full_name.strip()

        membership = cast(Any, db.execute(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == invite.organization_id,
                OrganizationMembership.user_id == user.id,
            )
        ).scalar_one_or_none())
        if membership is None:
            membership = OrganizationMembership(
                organization_id=invite.organization_id,
                user_id=user.id,
                role=invite.role,
                is_active=True,
            )
            db.add(membership)
        else:
            membership.is_active = True
            membership.role = invite.role or membership.role

        invite.accepted_at = now
        db.commit()

        claims = _resolve_user_claims_from_db(db, str(user.email))

    if claims is None:
        raise HTTPException(status_code=500, detail="Could not initialize invited user claims")
    return claims

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
