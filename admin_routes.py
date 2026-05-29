"""
Admin routes for NAPS Chatbot.
"""

import os
import io
import re
import jwt
import json
import asyncio
import secrets
import pypdf
import docx as docxlib
from datetime import datetime, timedelta

from fastapi import APIRouter, Request, Form, UploadFile, File, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, desc, update

from database.engine import get_session
from database.models import RagChunk, SystemPrompt, Conversation, UploadedDocument, KnowledgeSource
from rag.embedder import embed

from core.preprocessing import clean_text
from core.scraper import scrape_and_index
from cache.redis_client import get_redis, get_history, set_history, clear_history
from core.security import verify_password, limiter
from core.advanced_security.logging import log_audit_event
import logging

logger = logging.getLogger("naps-chatbot")

router    = APIRouter(prefix="/admin", tags=["Admin"])
templates = Jinja2Templates(directory="templates")

ADMIN_USER      = os.getenv("ADMIN_USER", "admin")
# Supports bcrypt hash (preferred) or plain fallback for dev
ADMIN_PASS_HASH = os.getenv("ADMIN_PASS_HASH", "")  # bcrypt hash
ADMIN_PASS_PLAIN= os.getenv("ADMIN_PASS", "admin123")  # plain fallback (dev only)
JWT_SECRET      = os.getenv("CHAT_JWT_SECRET", secrets.token_hex(32))
ALGORITHM      = "HS256"
IS_PRODUCTION   = os.getenv("ENV", "production") == "production"


def _check_password(plain: str) -> bool:
    """Verify admin password. Prefers bcrypt hash, falls back to plain for dev."""
    if ADMIN_PASS_HASH:
        return verify_password(plain, ADMIN_PASS_HASH)
    # Dev fallback: plain comparison (constant-time)
    return secrets.compare_digest(plain, ADMIN_PASS_PLAIN)



def _verify_admin(request: Request) -> bool:
    """Quick cookie-based admin check for routes not using Depends(require_admin)."""
    token = request.cookies.get("admin_token")
    if not token:
        return False
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        return payload.get("role") == "admin"
    except Exception:
        return False


def _make_token() -> str:
    payload = {"role": "admin", "exp": datetime.utcnow() + timedelta(hours=8)}
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)

async def require_admin(request: Request):
    """Dependency to enforce admin authentication with redirect for browser GETs. Includes Zero-Trust checks."""
    token = request.cookies.get("admin_token")
    
    if not token:
        if request.method == "GET":
            return RedirectResponse("/admin/login")
        log_audit_event("ZERO_TRUST_VIOLATION", request, details={"reason": "missing_token"})
        raise HTTPException(status_code=401, detail="Non authentifié")
        
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        if payload.get("role") != "admin":
            log_audit_event("ZERO_TRUST_VIOLATION", request, user_id=payload.get("sub"), details={"reason": "invalid_role"})
            raise HTTPException(status_code=403, detail="Accès refusé")
            
        # Zero-Trust Stub: Check if the IP or device fingerprint changed since login
        if payload.get("ip") != request.client.host and IS_PRODUCTION:
            log_audit_event("ZERO_TRUST_VIOLATION", request, user_id=payload.get("sub"), details={"reason": "ip_mismatch"})
            raise HTTPException(status_code=401, detail="Session invalidée pour des raisons de sécurité")
            
        return payload
    except Exception as e:
        log_audit_event("AUTH_FAILURE", request, details={"reason": str(e)})
        if request.method == "GET":
            return RedirectResponse("/admin/login")
        raise HTTPException(status_code=401, detail="Session invalide ou expirée")


# ── Login ─────────────────────────────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "admin/login.html", {"error": None})

@router.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username != ADMIN_USER or not _check_password(password):
        log_audit_event("AUTH_FAILURE", request, user_id=username, details={"reason": "invalid_credentials"})
        return templates.TemplateResponse(request, "admin/login.html", {"error": "Identifiants incorrects"})

    log_audit_event("AUTH_SUCCESS", request, user_id=username)
    
    # Embed IP in token for Zero-Trust validation
    payload = {"role": "admin", "exp": datetime.utcnow() + timedelta(hours=8), "ip": request.client.host}
    token = jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)
    
    response = RedirectResponse("/admin/dashboard", status_code=302)
    response.set_cookie("admin_token", token, httponly=True, max_age=28800, secure=IS_PRODUCTION, samesite="lax")
    return response

@router.get("/logout")
async def logout():
    response = RedirectResponse("/admin/login", status_code=302)
    response.delete_cookie("admin_token")
    return response


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, session: AsyncSession = Depends(get_session), _ = Depends(require_admin)):
    total_msgs = await session.scalar(select(func.count()).select_from(Conversation)) or 0
    today      = datetime.utcnow().date()
    msgs_today = await session.scalar(select(func.count()).select_from(Conversation).where(func.date(Conversation.created_at) == today)) or 0
    cache_hits = await session.scalar(select(func.count()).select_from(Conversation).where(Conversation.cache_hit == True)) or 0
    hit_rate   = round((cache_hits / total_msgs * 100) if total_msgs else 0, 1)
    avg_lat    = await session.scalar(select(func.avg(Conversation.latency_ms)))
    chunks_cnt = await session.scalar(select(func.count()).select_from(RagChunk)) or 0
    
    # Language distribution
    lang_rows  = await session.execute(select(Conversation.language, func.count().label("cnt")).group_by(Conversation.language).order_by(desc("cnt")).limit(6))
    lang_dist  = [{"lang": r.language or "fr", "cnt": r.cnt} for r in lang_rows]

    # Platform distribution (New)
    plat_rows  = await session.execute(select(Conversation.platform, func.count().label("cnt")).group_by(Conversation.platform).order_by(desc("cnt")))
    plat_dist  = [{"platform": r.platform or "ui", "cnt": r.cnt} for r in plat_rows]

    # Latest 5 conversations (Grouped by user)
    latest_rows = await session.execute(
        select(
            Conversation.user_id,
            func.max(Conversation.platform).label("platform"),
            func.count(Conversation.id).label("msgs"),
            func.max(Conversation.created_at).label("last_activity")
        )
        .group_by(Conversation.user_id)
        .order_by(desc("last_activity"))
        .limit(5)
    )
    latest_conversations = [
        {
            "user_id": r.user_id,
            "platform": r.platform or "unknown",
            "msgs": r.msgs,
            "last_activity": r.last_activity
        }
        for r in latest_rows
    ]

    # Top Leads (New)
    lead_rows = await session.execute(
        select(Conversation.user_id, func.count(Conversation.id).label("cnt"))
        .group_by(Conversation.user_id)
        .order_by(desc("cnt"))
        .limit(5)
    )
    top_leads = [{"user_id": r.user_id, "cnt": r.cnt} for r in lead_rows]

    # RAG Category Distribution (New)
    cat_rows = await session.execute(
        select(RagChunk.category, func.count(RagChunk.id).label("cnt"))
        .group_by(RagChunk.category)
        .order_by(desc("cnt"))
    )
    cat_dist = [{"category": r.category or "general", "cnt": r.cnt} for r in cat_rows]

    return templates.TemplateResponse(request, "admin/dashboard.html", {
        "msgs_today": msgs_today, "hit_rate": hit_rate,
        "avg_lat": round(avg_lat / 1000, 1) if avg_lat else 0,
        "chunks_cnt": chunks_cnt, "total_msgs": total_msgs, "lang_dist": lang_dist,
        "plat_dist": plat_dist, "latest_conversations": latest_conversations,
        "top_leads": top_leads, "cat_dist": cat_dist
    })


# ── Chunks CRUD ───────────────────────────────────────────────────────────────

@router.get("/chunks", response_class=HTMLResponse)
async def chunks_list(request: Request, session: AsyncSession = Depends(get_session), _ = Depends(require_admin)):
    result = await session.execute(select(RagChunk).order_by(desc(RagChunk.id)))
    return templates.TemplateResponse(request, "admin/chunks.html", {"chunks": result.scalars().all()})

@router.post("/chunks/add")
async def chunk_add(request: Request, content: str = Form(...), category: str = Form("general"), source: str = Form("manual"), session: AsyncSession = Depends(get_session), _ = Depends(require_admin)):
    session.add(RagChunk(content=content, embedding=embed(content), category=category, source=source, language="fr"))
    await session.commit()
    return RedirectResponse("/admin/chunks", status_code=302)

@router.post("/chunks/edit/{chunk_id}")
async def chunk_edit(chunk_id: int, request: Request, content: str = Form(...), category: str = Form("general"), session: AsyncSession = Depends(get_session), _ = Depends(require_admin)):
    chunk = await session.get(RagChunk, chunk_id)
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")
    chunk.content = content
    chunk.category = category
    chunk.embedding = embed(content)
    chunk.updated_at = datetime.utcnow()
    await session.commit()
    return RedirectResponse("/admin/chunks", status_code=302)

@router.post("/chunks/delete/{chunk_id}")
async def chunk_delete(chunk_id: int, request: Request, session: AsyncSession = Depends(get_session), _ = Depends(require_admin)):
    await session.execute(delete(RagChunk).where(RagChunk.id == chunk_id))
    await session.commit()
    return RedirectResponse("/admin/chunks", status_code=302)


# ── Upload ────────────────────────────────────────────────────────────────────

@router.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request, session: AsyncSession = Depends(get_session)):
    if not _verify_admin(request):
        return RedirectResponse("/admin/login")
    result = await session.execute(select(UploadedDocument).order_by(desc(UploadedDocument.id)))
    docs = result.scalars().all()
    return templates.TemplateResponse(request, "admin/upload.html", {"documents": docs})

@router.post("/upload")
async def upload_file(
    request: Request, 
    file: UploadFile = File(...), 
    category: str = Form("general"), 
    session: AsyncSession = Depends(get_session),
    _ = Depends(require_admin)
):
    # 10MB limit
    MAX_SIZE = 10 * 1024 * 1024
    content_bytes = await file.read()
    if len(content_bytes) > MAX_SIZE:
        raise HTTPException(status_code=413, detail="Fichier trop volumineux (max 10MB)")
    
    # 1. Create Document Entry
    doc = UploadedDocument(filename=file.filename, category=category)
    session.add(doc)
    await session.flush() # Get ID
    
    content_bytes = await file.read()
    ext = file.filename.rsplit(".", 1)[-1].lower()
    raw_text = ""
    
    if ext in ("txt", "md"):
        raw_text = content_bytes.decode("utf-8", errors="ignore")
    elif ext == "pdf":
        reader = pypdf.PdfReader(io.BytesIO(content_bytes))
        raw_text = "\n".join(p.extract_text() or "" for p in reader.pages)
    elif ext in ("doc", "docx"):
        doc_lib = docxlib.Document(io.BytesIO(content_bytes))
        raw_text = "\n".join(p.text for p in doc_lib.paragraphs if p.text.strip())
    else:
        return JSONResponse({"error": f"Format .{ext} non supporté"}, status_code=400)

    # 2. Preprocessing & Chunking
    # Split by sentences or paragraphs
    segments = [s.strip() for s in raw_text.replace("\n", " ").split(".") if len(s.strip()) > 30]
    batch = []
    for s in segments:
        cleaned = clean_text(s)
        batch.append(RagChunk(
            content=s + ".", 
            embedding=embed(cleaned), # Use cleaned for search, original for display
            category=category, 
            source=file.filename,
            document_id=doc.id,
            language="fr"
        ))
    
    session.add_all(batch)
    await session.commit()
    return JSONResponse({"status": "ok", "chunks_added": len(batch), "filename": file.filename})


@router.post("/document/delete/{doc_id}")
async def document_delete(doc_id: int, request: Request, session: AsyncSession = Depends(get_session)):
    if not _verify_admin(request):
        return RedirectResponse("/admin/login")
    
    # Cascade delete: Chunks first
    await session.execute(delete(RagChunk).where(RagChunk.document_id == doc_id))
    # Then document
    await session.execute(delete(UploadedDocument).where(UploadedDocument.id == doc_id))
    
    await session.commit()
    return RedirectResponse("/admin/upload", status_code=302)


# ── RAG Test ─────────────────────────────────────────────────────────────────

@router.get("/rag-test", response_class=HTMLResponse)
async def rag_test_page(request: Request, _ = Depends(require_admin)):
    return templates.TemplateResponse(request, "admin/rag_test.html", {"results": None})

@router.post("/rag-test", response_class=HTMLResponse)
async def rag_test_run(request: Request, query: str = Form(...), session: AsyncSession = Depends(get_session)):
    if not _verify_admin(request):
        return RedirectResponse("/admin/login")
    import numpy as np
    from rag.retriever import retrieve
    query_vec = embed(query)
    result    = await session.execute(select(RagChunk))
    chunks    = result.scalars().all()
    if not chunks:
        return templates.TemplateResponse(request, "admin/rag_test.html", {"query": query, "results": None, "error": "Base vide."})
    scores   = (np.array([c.embedding for c in chunks]) @ np.array(query_vec)).tolist()
    top5_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:5]
    top5     = [{"content": chunks[i].content, "category": chunks[i].category, "score": round(scores[i], 3)} for i in top5_idx if scores[i] > 0.2]
    reranked = await retrieve(query, session)
    return templates.TemplateResponse(request, "admin/rag_test.html", {"query": query, "top5": top5, "reranked": reranked})


# ── System Prompt ─────────────────────────────────────────────────────────────

@router.get("/prompt", response_class=HTMLResponse)
async def prompt_page(request: Request, session: AsyncSession = Depends(get_session), _ = Depends(require_admin)):
    result = await session.execute(select(SystemPrompt).order_by(desc(SystemPrompt.id)))
    return templates.TemplateResponse(request, "admin/prompt.html", {"prompts": result.scalars().all()})

@router.post("/prompt/save")
async def prompt_save(
    request: Request, 
    content: str = Form(...), 
    language: str = Form("fr"),
    note: str = Form(""), 
    session: AsyncSession = Depends(get_session),
    _ = Depends(require_admin)
):
    # Deactivate current active prompt for this language
    await session.execute(
        update(SystemPrompt)
        .where(SystemPrompt.language == language)
        .values(is_active=False)
    )
    
    max_ver = await session.scalar(
        select(func.max(SystemPrompt.version)).where(SystemPrompt.language == language)
    ) or 0
    
    session.add(SystemPrompt(
        content=content, 
        language=language,
        note=note, 
        is_active=True, 
        version=max_ver + 1, 
        created_by="admin"
    ))
    await session.commit()
    return RedirectResponse("/admin/prompt", status_code=302)

@router.post("/prompt/rollback/{prompt_id}")
async def prompt_rollback(prompt_id: int, request: Request, session: AsyncSession = Depends(get_session)):
    if not _verify_admin(request):
        return RedirectResponse("/admin/login")
    for p in (await session.execute(select(SystemPrompt))).scalars().all():
        p.is_active = (p.id == prompt_id)
    await session.commit()
    return RedirectResponse("/admin/prompt", status_code=302)


# ── Cache ─────────────────────────────────────────────────────────────────────

@router.get("/cache", response_class=HTMLResponse)
async def cache_page(request: Request, session: AsyncSession = Depends(get_session), _ = Depends(require_admin)):
    r = await get_redis()
    entries = []
    if r:
        for key in await r.keys("naps:cache:*"):
            raw = await r.get(key)
            ttl = await r.ttl(key)
            if raw:
                try:
                    data = json.loads(raw)
                    entries.append({"key": key, "answer": data.get("answer", "")[:120] + "…", "ttl": ttl})
                except Exception:
                    pass
    total    = await session.scalar(select(func.count()).select_from(Conversation)) or 0
    hits     = await session.scalar(select(func.count()).select_from(Conversation).where(Conversation.cache_hit == True)) or 0
    hit_rate = round((hits / total * 100) if total else 0, 1)
    return templates.TemplateResponse(request, "admin/cache.html", {"entries": entries, "hit_rate": hit_rate, "total": total, "hits": hits})

@router.post("/cache/delete")
async def cache_delete(request: Request, key: str = Form(...), _ = Depends(require_admin)):
    r = await get_redis()
    r = await get_redis()
    if r:
        await r.delete(key)
    return RedirectResponse("/admin/cache", status_code=302)


# ── Knowledge Sources ─────────────────────────────────────────────────────────

@router.get("/sources", response_class=HTMLResponse)
async def sources_page(request: Request, session: AsyncSession = Depends(get_session), _ = Depends(require_admin)):
    result = await session.execute(select(KnowledgeSource).order_by(desc(KnowledgeSource.id)))
    sources = result.scalars().all()
    return templates.TemplateResponse(request, "admin/sources.html", {"sources": sources})


@router.post("/sources/add")
async def source_add(request: Request, url: str = Form(...), name: str = Form(""), session: AsyncSession = Depends(get_session)):
    if not _verify_admin(request):
        return RedirectResponse("/admin/login")
    
    # Check if exists
    exists = await session.execute(select(KnowledgeSource).where(KnowledgeSource.url == url))
    if exists.scalar():
        return RedirectResponse("/admin/sources?error=exists", status_code=302)
        
    session.add(KnowledgeSource(url=url, name=name))
    await session.commit()
    return RedirectResponse("/admin/sources", status_code=302)


@router.post("/sources/scrape/{source_id}")
async def source_trigger_scrape(source_id: int, request: Request, session: AsyncSession = Depends(get_session)):
    if not _verify_admin(request):
        return RedirectResponse("/admin/login")
        
    source = await session.get(KnowledgeSource, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
        
    # Background task or immediate for now
    try:
        await scrape_and_index(source.id, source.url, session)
        return RedirectResponse("/admin/sources?success=scraped", status_code=302)
    except Exception as e:
        return RedirectResponse(f"/admin/sources?error={str(e)}", status_code=302)


@router.post("/sources/delete/{source_id}")
async def source_delete(source_id: int, request: Request, session: AsyncSession = Depends(get_session)):
    if not _verify_admin(request):
        return RedirectResponse("/admin/login")
        
    # Delete chunks associated with this source URL
    source = await session.get(KnowledgeSource, source_id)
    if source:
        await session.execute(delete(RagChunk).where(RagChunk.source == source.url))
        await session.execute(delete(KnowledgeSource).where(KnowledgeSource.id == source_id))
        await session.commit()
        
    return RedirectResponse("/admin/sources", status_code=302)


# ── Conversations ─────────────────────────────────────────────────────────────

@router.get("/conversations", response_class=HTMLResponse)
async def conversations_list(request: Request, session: AsyncSession = Depends(get_session), _ = Depends(require_admin)):
    # Get unique users from DB
    result = await session.execute(
        select(
            Conversation.user_id, 
            func.max(Conversation.created_at).label("last_seen"),
            func.count(Conversation.id).label("msg_count")
        ).group_by(Conversation.user_id).order_by(desc("last_seen"))
    )
    users = result.all()
    return templates.TemplateResponse(request, "admin/conversations.html", {"users": users})


@router.get("/conversations/{user_id}", response_class=HTMLResponse)
async def conversation_detail(user_id: str, request: Request, _ = Depends(require_admin)):
    history = await get_history(user_id, max_turns=50)
    return templates.TemplateResponse(request, "admin/conversation_detail.html", {
        "user_id": user_id,
        "history": history
    })


@router.post("/conversations/{user_id}/save")
async def conversation_save(user_id: str, request: Request):
    if not _verify_admin(request):
        return RedirectResponse("/admin/login")
    
    form = await request.form()
    # Reconstruct history from form fields
    roles    = form.getlist("role[]")
    contents = form.getlist("content[]")
    
    new_history = []
    for r, c in zip(roles, contents):
        if c.strip():
            new_history.append({"role": r, "content": c})
            
    await set_history(user_id, new_history)
    return RedirectResponse(f"/admin/conversations/{user_id}", status_code=302)


@router.post("/conversations/{user_id}/clear")
async def conversation_clear(user_id: str, request: Request):
    if not _verify_admin(request):
        return RedirectResponse("/admin/login")
    
    await clear_history(user_id)
    return RedirectResponse("/admin/conversations", status_code=302)

@router.post("/cache/flush")
async def cache_flush(request: Request):
    if not _verify_admin(request):
        return RedirectResponse("/admin/login")
    r = await get_redis()
    if r:
        keys = await r.keys("naps:cache:*")
        if keys:
            await r.delete(*keys)
    return RedirectResponse("/admin/cache", status_code=302)