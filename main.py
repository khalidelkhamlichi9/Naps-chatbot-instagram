"""
Chatbot NAPS — Production FastAPI Application
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request
from fastapi.responses import StreamingResponse, RedirectResponse, Response, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from pydantic import BaseModel
import logging
import time
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("naps-chatbot")

from database.engine import init_db, get_session
from rag.embedder import load_embedder
from llm.deepseek import init_http_client, close_http_client
from instagram.sender import init_sender_client, close_sender_client
from instagram.webhook import router as webhook_router
from admin_routes import router as admin_router
from cache.redis_client import get_redis, close_redis
from core.pipeline import process_message
from core.security import limiter, get_current_user
from core.advanced_security.validation import validate_and_sanitize
from core.advanced_security.logging import log_audit_event
from sqlalchemy.ext.asyncio import AsyncSession

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Chatbot NAPS...")
    init_http_client()
    init_sender_client()
    
    # Initialisation de la DB avec gestion d'erreur
    try:
        await init_db()
        logger.info("Database synced successfully.")
    except Exception as e:
        logger.error(f"Database sync failed: {e}")

    # Initialisation de Redis
    try:
        await get_redis()
    except Exception as e:
        logger.warning(f"Redis initialization failed: {e}")

    logger.info("Chatbot NAPS ready!")
    yield
    logger.info("Shutting down...")
    await close_http_client()
    await close_sender_client()
    await close_redis()

IS_PRODUCTION = os.getenv("ENV", "production") == "production"

app = FastAPI(
    title="Chatbot NAPS",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None,
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS — Restricted Origins ────────────────────────────────────────────────────
ALLOWED_ORIGINS = [
    "https://naps.astraldigital.ma",
    "https://naps.ma",
]
if not IS_PRODUCTION:
    ALLOWED_ORIGINS += ["http://localhost:8000", "http://127.0.0.1:8000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
)

# ── Security Headers Middleware ────────────────────────────────────────────────────
# Paths that skip heavy processing (health probes, static assets)
_SKIP_AUDIT_PATHS = {"/health", "/favicon.ico"}

@app.middleware("http")
async def advanced_security_middleware(request: Request, call_next):
    t0 = time.monotonic()
    path = request.url.path

    # Skip audit logging for lightweight health/probe endpoints
    if path not in _SKIP_AUDIT_PATHS:
        log_audit_event("HTTP_REQUEST", request, details={"path": path, "method": request.method})

    response = await call_next(request)

    # Add response time header (useful for monitoring)
    elapsed_ms = round((time.monotonic() - t0) * 1000, 2)
    response.headers["X-Response-Time"] = f"{elapsed_ms}ms"

    # Skip heavy headers for health endpoint (keeps probe latency minimal)
    if path in _SKIP_AUDIT_PATHS:
        return response

    # Anti-XSS & anti-sniffing
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    # HSTS — force HTTPS for 1 year
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    # Content Security Policy
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )
    # Remove technology fingerprinting headers
    if "server" in response.headers:
        del response.headers["server"]
    if "x-powered-by" in response.headers:
        del response.headers["x-powered-by"]
    # Keep ngrok skip header for development
    if not IS_PRODUCTION:
        response.headers["ngrok-skip-browser-warning"] = "true"
    return response

app.include_router(webhook_router)
app.include_router(admin_router)
app.mount("/static", StaticFiles(directory="static"), name="static")

class ChatRequest(BaseModel):
    message: str
    user_id: str = "anonymous"
    stream:  bool = False

class ChatResponse(BaseModel):
    answer:     str
    language:   str | None = None
    latency_ms: float | None = None

@app.post("/chat")
@limiter.limit("20/minute")
async def chat(request: Request, body: ChatRequest, session: AsyncSession = Depends(get_session), user: dict = Depends(get_current_user)):
    t_start  = time.monotonic()
    user_id  = user.get("sub", body.user_id)
    
    # 1. Sanitize input
    try:
        sanitized_data = validate_and_sanitize({"message": body.message})
        safe_message = sanitized_data["message"]
    except Exception as e:
        log_audit_event("INJECTION_ATTEMPT", request, user_id, details={"raw_message": body.message})
        raise
        
    from core.language import detect_language
    language = detect_language(safe_message)

    if body.stream:
        generator = await process_message(message=safe_message, user_id=user_id, session=session, stream=True)
        async def sse():
            async for chunk in generator:
                yield f"data: {chunk}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(sse(), media_type="text/event-stream")

    answer  = await process_message(message=safe_message, user_id=user_id, session=session, stream=False)
    latency = round((time.monotonic() - t_start) * 1000, 2)
    return ChatResponse(answer=answer, language=language, latency_ms=latency)

@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse("/admin/login")

_templates = Jinja2Templates(directory="templates")

@app.get("/ui", response_class=HTMLResponse, include_in_schema=False)
async def chatbot_ui(request: Request):
    import uuid as _uuid
    response = _templates.TemplateResponse(request, "chatbot.html", {})
    # Set a UUID session cookie if not already present (replaces Referer-based auth)
    if not request.cookies.get("ui_session"):
        session_id = str(_uuid.uuid4())
        response.set_cookie(
            "ui_session",
            session_id,
            httponly=True,
            secure=IS_PRODUCTION,
            samesite="lax",
            max_age=86400,  # 24 hours
        )
    return response

@app.get("/admin", include_in_schema=False)
async def admin_redirect():
    return RedirectResponse("/admin/login")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
        '<rect width="32" height="32" rx="6" fill="#ffffff"/>'
        '<text x="50%" y="50%" dominant-baseline="central" text-anchor="middle" '
        'font-size="18" font-family="sans-serif" fill="#e25200" font-weight="bold">N</text>'
        '</svg>'
    )
    return Response(content=svg, media_type="image/svg+xml")

@app.get("/health", include_in_schema=False)
async def health():
    return {"status": "ok"}

@app.post("/chat/clear", include_in_schema=False)
@limiter.limit("5/minute")
async def chat_clear(request: Request, body: ChatRequest):
    """Clear history for a specific user — rate-limited, user_id sanitized."""
    from cache.redis_client import clear_history
    from core.security import sanitize_user_id
    user_id = sanitize_user_id(body.user_id) or "ui-user"
    await clear_history(user_id)
    return {"status": "cleared"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False, workers=1)
