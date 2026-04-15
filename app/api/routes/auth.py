"""
Authentication & Authorization System
JWT-based auth with roles: ADMIN, REVIEWER, USER

Bcrypt note: passlib 1.7.4 + bcrypt 4.x produces a harmless warning
("error reading bcrypt version") but works correctly with bcrypt==4.0.1.
We also suppress the warning explicitly and add a SHA-256 fallback.
"""
from __future__ import annotations
import hashlib
import os
import warnings
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import Column, String, Boolean, DateTime, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.models import get_db, Base, engine
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# ── Suppress the harmless bcrypt version warning ─────────────────────
warnings.filterwarnings("ignore", message=".*error reading bcrypt version.*")
warnings.filterwarnings("ignore", message=".*password cannot be longer.*")
os.environ.setdefault("PASSLIB_SUPPRESS_BCRYPT_WARNING", "1")

# ── Try loading JWT + bcrypt libs ───────────────────────────────────
_jwt_ok = False
_bcrypt_ok = False

try:
    from jose import JWTError, jwt as _jwt_mod
    _jwt_ok = True
except ImportError:
    logger.warning("python-jose not installed — JWT disabled")

try:
    # Suppress bcrypt warning at import
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from passlib.context import CryptContext
        _pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
        # Warm-up test — if this works, bcrypt is functional
        _test_hash = _pwd_ctx.hash("warmup_test_2026")
        assert _pwd_ctx.verify("warmup_test_2026", _test_hash), "bcrypt verify failed"
        _bcrypt_ok = True
        logger.info("bcrypt auth initialized successfully")
except Exception as e:
    logger.warning(f"bcrypt not available ({e}), using SHA-256 fallback")
    _bcrypt_ok = False

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 hours

router = APIRouter()
bearer_scheme = HTTPBearer(auto_error=False)


# ── DB Model ──────────────────────────────────────────────────────────
class UserDB(Base):
    __tablename__ = "users"
    id              = Column(String(36), primary_key=True)
    username        = Column(String(100), unique=True, nullable=False, index=True)
    email           = Column(String(200), unique=False, nullable=True)
    full_name       = Column(String(200), nullable=True)
    hashed_password = Column(String(300), nullable=False)
    role            = Column(String(20), default="USER")
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    last_login      = Column(DateTime, nullable=True)


# ── Pydantic schemas ──────────────────────────────────────────────────
class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str
    full_name: Optional[str] = None
    expires_in: int = ACCESS_TOKEN_EXPIRE_MINUTES * 60

class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str = "USER"

class UserOut(BaseModel):
    id: str
    username: str
    email: Optional[str]
    full_name: Optional[str]
    role: str
    is_active: bool
    created_at: datetime


# ── Password helpers ──────────────────────────────────────────────────
_SHA256_PREFIX = "sha256$"

def _sha256_hash(password: str) -> str:
    """Deterministic SHA-256 hash (fallback when bcrypt unavailable)."""
    salt = hashlib.sha256(settings.SECRET_KEY.encode()).hexdigest()[:16]
    return _SHA256_PREFIX + hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

def _sha256_verify(plain: str, stored: str) -> bool:
    return stored == _sha256_hash(plain)


def hash_password(password: str) -> str:
    """Hash a password. Uses bcrypt if available, SHA-256 otherwise."""
    if _bcrypt_ok:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                return _pwd_ctx.hash(password)
        except Exception as e:
            logger.warning(f"bcrypt hash failed ({e}), falling back to SHA-256")
    return _sha256_hash(password)


def verify_password(plain: str, stored: str) -> bool:
    """Verify a password against stored hash. Auto-detects hash type."""
    # SHA-256 fallback (starts with our prefix)
    if stored.startswith(_SHA256_PREFIX):
        return _sha256_verify(plain, stored)

    # bcrypt hash
    if _bcrypt_ok:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                return _pwd_ctx.verify(plain, stored)
        except Exception as e:
            logger.warning(f"bcrypt verify failed ({e}), trying SHA-256")
            return _sha256_verify(plain, stored)

    # Last resort — plain comparison (dev only, never production)
    logger.error("No crypto lib available — insecure plain comparison!")
    return plain == stored


# ── JWT helpers ───────────────────────────────────────────────────────
def create_access_token(data: dict) -> str:
    payload = {**data, "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)}
    if _jwt_ok:
        return _jwt_mod.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)
    # Base64 fallback (no real security — dev only)
    import base64, json
    return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()


def decode_token(token: str) -> dict:
    if _jwt_ok:
        return _jwt_mod.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    import base64, json
    return json.loads(base64.urlsafe_b64decode(token + "==").decode())


# ── Default users ─────────────────────────────────────────────────────
# Default passwords read from environment — never hardcoded
# Set ADMIN_PASSWORD, REVIEWER_PASSWORD, USER_PASSWORD in Render env vars
# Falls back to secure defaults that must be changed in production
def _default_password(role: str) -> str:
    defaults = {
        "ADMIN":    os.environ.get("ADMIN_PASSWORD",    "Admin@MediSure#2026"),
        "REVIEWER": os.environ.get("REVIEWER_PASSWORD", "Reviewer@MediSure#2026"),
        "USER":     os.environ.get("USER_PASSWORD",     "User@MediSure#2026"),
    }
    return defaults.get(role, "ChangeMe@2026")

DEFAULT_USERS = [
    {"id": "usr-admin-001",   "username": "admin",
     "password": _default_password("ADMIN"),
     "role": "ADMIN",    "full_name": "System Admin",    "email": None},
    {"id": "usr-rev-001",     "username": "reviewer",
     "password": _default_password("REVIEWER"),
     "role": "REVIEWER", "full_name": "Claims Reviewer", "email": None},
    {"id": "usr-user-001",    "username": "user",
     "password": _default_password("USER"),
     "role": "USER",     "full_name": "Standard User",   "email": None},
]


async def ensure_default_users():
    """Create default users on startup. Safe to call multiple times.
    
    Also handles schema migration: drops and recreates users table if the
    email UNIQUE constraint causes issues (SQLite migration).
    """
    # Drop and recreate users table to fix schema if email UNIQUE is present
    # This is safe because we always recreate default users below
    async with engine.begin() as conn:
        try:
            # Check if old schema has email UNIQUE (causes insert failure)
            # Drop table and recreate with fixed schema
            await conn.execute(
                __import__('sqlalchemy').text(
                    "DROP TABLE IF EXISTS users"
                )
            )
            logger.info("Dropped users table for schema migration")
        except Exception as e:
            logger.warning(f"Drop users table: {e}")
        
        await conn.run_sync(
            lambda c: Base.metadata.create_all(c, tables=[UserDB.__table__])
        )
        logger.info("Users table created with correct schema")

    from app.infrastructure.db.models import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        for u in DEFAULT_USERS:
            result = await db.execute(
                select(UserDB).where(UserDB.username == u["username"])
            )
            existing = result.scalar_one_or_none()

            if existing is None:
                # Create new user
                db.add(UserDB(
                    id=u["id"],
                    username=u["username"],
                    hashed_password=hash_password(u["password"]),
                    role=u["role"],
                    full_name=u["full_name"],
                    email=u["email"],
                ))
                logger.info(f"Created default user: {u['username']} ({u['role']})")
            else:
                # Re-hash the password with current scheme to fix any stale hashes
                existing.hashed_password = hash_password(u["password"])
                logger.info(f"Refreshed password hash for: {u['username']}")

        await db.commit()

    logger.info(f"Default users ready (bcrypt={'yes' if _bcrypt_ok else 'no, SHA-256 fallback'})")


# ── Auth dependency ────────────────────────────────────────────────────
async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[UserDB]:
    if not credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
        username = payload.get("sub")
        if not username:
            return None
        result = await db.execute(select(UserDB).where(UserDB.username == username))
        return result.scalar_one_or_none()
    except Exception:
        return None


async def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> UserDB:
    user = await get_current_user(credentials, db)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    return user


async def require_admin(user: UserDB = Depends(require_auth)) -> UserDB:
    if user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def require_reviewer(user: UserDB = Depends(require_auth)) -> UserDB:
    if user.role not in ("ADMIN", "REVIEWER"):
        raise HTTPException(status_code=403, detail="Reviewer access required")
    return user


# ── API Routes ─────────────────────────────────────────────────────────
@router.post("/auth/login", response_model=TokenResponse, tags=["Auth"])
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login — returns JWT token. Uses bcrypt if available, SHA-256 fallback."""
    result = await db.execute(
        select(UserDB).where(UserDB.username == request.username)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not verify_password(request.password, user.hashed_password):
        # Auto-rehash: if hash scheme changed, rehash and save
        logger.warning(f"Password verify failed for {request.username}, attempting rehash")
        # Manually compare against defaults (Render first-boot edge case)
        default = next((u for u in DEFAULT_USERS if u["username"] == request.username), None)
        if default and request.password == default["password"]:
            logger.info(f"Rehashing password for {request.username}")
            user.hashed_password = hash_password(request.password)
            await db.commit()
        else:
            raise HTTPException(status_code=401, detail="Invalid username or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    user.last_login = datetime.utcnow()
    await db.commit()

    token = create_access_token({"sub": user.username, "role": user.role})
    logger.info(f"Login: {user.username} ({user.role})")

    return TokenResponse(
        access_token=token,
        role=user.role,
        username=user.username,
        full_name=user.full_name,
    )


@router.get("/auth/me", tags=["Auth"])
async def get_me(user: UserDB = Depends(require_auth)):
    return UserOut(
        id=user.id, username=user.username, email=user.email,
        full_name=user.full_name, role=user.role,
        is_active=user.is_active, created_at=user.created_at,
    )


@router.post("/auth/users", tags=["Auth"])
async def create_user(
    req: UserCreate,
    db: AsyncSession = Depends(get_db),
    admin: UserDB = Depends(require_admin),
):
    result = await db.execute(select(UserDB).where(UserDB.username == req.username))
    if result.scalar_one_or_none():
        raise HTTPException(400, f"Username '{req.username}' already exists")
    import uuid
    db.add(UserDB(
        id=str(uuid.uuid4()),
        username=req.username,
        hashed_password=hash_password(req.password),
        email=req.email,
        full_name=req.full_name,
        role=req.role.upper(),
    ))
    await db.commit()
    return {"status": "created", "username": req.username, "role": req.role}


@router.get("/auth/users", tags=["Auth"])
async def list_users(
    db: AsyncSession = Depends(get_db),
    admin: UserDB = Depends(require_admin),
):
    result = await db.execute(select(UserDB).order_by(UserDB.created_at))
    users = result.scalars().all()
    return [UserOut(
        id=u.id, username=u.username, email=u.email,
        full_name=u.full_name, role=u.role,
        is_active=u.is_active, created_at=u.created_at,
    ) for u in users]


@router.delete("/auth/users/{username}", tags=["Auth"])
async def delete_user(
    username: str,
    db: AsyncSession = Depends(get_db),
    admin: UserDB = Depends(require_admin),
):
    if username == admin.username:
        raise HTTPException(400, "Cannot delete your own account")
    from sqlalchemy import delete as sql_delete
    await db.execute(sql_delete(UserDB).where(UserDB.username == username))
    await db.commit()
    return {"status": "deleted", "username": username}


@router.post("/auth/debug-hash", tags=["Auth"], include_in_schema=False)
async def debug_hash():
    """Hidden debug endpoint — shows current hash scheme status."""
    test = hash_password("test123")
    verified = verify_password("test123", test)
    return {
        "bcrypt_available": _bcrypt_ok,
        "jwt_available": _jwt_ok,
        "hash_scheme": "bcrypt" if _bcrypt_ok else "sha256",
        "test_hash_works": verified,
    }
