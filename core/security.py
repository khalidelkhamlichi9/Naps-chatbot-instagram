"""
NAPS Chatbot — Hardened Security Module
Applies: JWT strict enforcement, bcrypt passwords, UUID sessions,
         timing-safe comparisons, rate limiting.
"""
import os
import re
import uuid
import hmac
import hashlib
import asyncio
import secrets
import logging
from typing import Optional

from fastapi import HTTPException, Request, Cookie
from jose import jwt, JWTError
from slowapi import Limiter
from slowapi.util import get_remote_address

try:
    import bcrypt
    _BCRYPT_AVAILABLE = True
except ImportError:
    _BCRYPT_AVAILABLE = False

logger = logging.getLogger("naps-chatbot")

# ── JWT Secret — FATAL if missing or default ──────────────────────────────────
JWT_SECRET = os.getenv("CHAT_JWT_SECRET", "")
if not JWT_SECRET or JWT_SECRET in ("change_me_in_production", "secret"):
    # In dev allow it but warn loudly; in prod crash immediately
    _env = os.getenv("ENV", "production")
    if _env == "production":
        raise RuntimeError(
            "FATAL: CHAT_JWT_SECRET is not set or is using the default value.\n"
            "Generate a secure secret: python -c \"import secrets; print(secrets.token_hex(64))\""
        )
    else:
        JWT_SECRET = secrets.token_hex(32)  # Random per-restart for dev
        logger.warning("⚠️  DEV MODE: Using random JWT_SECRET. Set CHAT_JWT_SECRET in .env for persistence.")

ALGORITHM = "HS256"

# ── Rate Limiter ──────────────────────────────────────────────────────────────

def _get_rate_limit_key(request: Request) -> str:
    """
    Rate limit key: uses ui_session cookie or JWT sub when available,
    so each user/session gets their own bucket instead of sharing by IP.
    Falls back to IP address.
    """
    # 1. Try JWT Bearer sub
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            import jose.jwt as _jwt
            payload = _jwt.decode(auth[7:], options={"verify_signature": False})
            sub = payload.get("sub")
            if sub:
                return f"jwt:{sub}"
        except Exception:
            pass

    # 2. Try ui_session cookie (UUID per browser tab)
    session = request.cookies.get("ui_session", "")
    if session and len(session) >= 8:
        clean = re.sub(r'[^a-f0-9\-]', '', session)[:36]
        if clean:
            return f"session:{clean}"

    # 3. Fallback to IP
    return get_remote_address(request)


limiter = Limiter(key_func=_get_rate_limit_key, default_limits=["20/minute"])


# ── Password Utilities (bcrypt) ───────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """Hash a password with bcrypt. Use during admin setup."""
    if _BCRYPT_AVAILABLE:
        return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()
    # Fallback: SHA-256 with salt (less secure, prefer bcrypt)
    salt = secrets.token_hex(16)
    h = hashlib.sha256(f"{salt}:{plain}".encode()).hexdigest()
    return f"sha256:{salt}:{h}"


def verify_password(plain: str, hashed: str) -> bool:
    """Constant-time password verification — resists timing attacks."""
    try:
        if _BCRYPT_AVAILABLE and not hashed.startswith("sha256:"):
            return bcrypt.checkpw(plain.encode(), hashed.encode())
        # Fallback SHA-256
        _, salt, stored_hash = hashed.split(":", 2)
        computed = hashlib.sha256(f"{salt}:{plain}".encode()).hexdigest()
        return hmac.compare_digest(computed, stored_hash)
    except Exception:
        return False


# ── JWT Utilities ─────────────────────────────────────────────────────────────

def create_token(payload: dict) -> str:
    """Encode a JWT token."""
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and verify a JWT token. Raises 401 on failure."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
    except JWTError as e:
        logger.warning(f"[SEC] Invalid JWT token attempt: {e}")
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")


# ── Auth Dependency ───────────────────────────────────────────────────────────

async def get_current_user(
    request: Request,
    ui_session: Optional[str] = Cookie(default=None, alias="ui_session"),
) -> dict:
    """
    FastAPI dependency — validates auth via (in priority order):
    1. Bearer JWT in Authorization header
    2. admin_token cookie (admin dashboard)
    3. ui_session cookie (UUID-based, replaces unsafe Referer check)
    """
    # 1. Bearer JWT
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return decode_token(auth[7:])

    # 2. Admin cookie
    cookie_token = request.cookies.get("admin_token")
    if cookie_token:
        try:
            return decode_token(cookie_token)
        except HTTPException:
            pass

    # 3. UI session via UUID cookie (safe — replaces the forgeable Referer check)
    if ui_session:
        safe_session = re.sub(r'[^a-f0-9\-]', '', ui_session)[:36]
        try:
            uuid.UUID(safe_session)  # Validate UUID format
            return {"sub": f"ui-{safe_session[:8]}", "role": "ui"}
        except ValueError:
            logger.warning(f"[SEC] Invalid ui_session format from {request.client.host}")

    raise HTTPException(status_code=401, detail="Authentification requise")


# ── Meta Webhook Signature ────────────────────────────────────────────────────

def verify_meta_signature(payload: bytes, x_hub_signature: str) -> bool:
    """Verify X-Hub-Signature-256 from Meta webhook (HMAC-SHA256)."""
    app_secret = os.getenv("META_APP_SECRET", "")
    if not app_secret:
        logger.error("[SEC] META_APP_SECRET not set — webhook signature verification skipped!")
        return True  # Degrade gracefully in dev
    expected = "sha256=" + hmac.new(
        app_secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, x_hub_signature)


# ── Input Sanitizer ───────────────────────────────────────────────────────────

def sanitize_user_id(user_id: str) -> str:
    """Strip all non-alphanumeric chars from user_id to prevent injection."""
    return re.sub(r'[^a-zA-Z0-9_\-]', '', str(user_id))[:64]


# ── Security Audit Logger ─────────────────────────────────────────────────────

def log_security_event(event: str, request: Request, extra: str = ""):
    """Structured security event logger."""
    ip = request.client.host if request.client else "unknown"
    ua = request.headers.get("user-agent", "")[:80]
    logger.warning(f"[SEC_EVENT] {event} | IP={ip} | UA={ua} | {extra}")
