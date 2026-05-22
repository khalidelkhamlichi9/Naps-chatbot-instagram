import json
import numpy as np
import redis.asyncio as aioredis
from typing import Optional
import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger("naps-chatbot")

load_dotenv()

REDIS_URL              = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CACHE_THRESHOLD        = float(os.getenv("CACHE_SIMILARITY_THRESHOLD", "0.92"))
SESSION_TTL            = 60 * 60 * 24   # 24 hours
CACHE_PREFIX           = "naps:cache:"
SESSION_PREFIX         = "naps:session:"

_redis: Optional[aioredis.Redis] = None


async def get_redis() -> Optional[aioredis.Redis]:
    global _redis
    if _redis is None:
        try:
            _redis = await aioredis.from_url(REDIS_URL, decode_responses=True)
            await _redis.ping()
        except Exception as e:
            logger.warning(f"Redis unavailable: {e}")
            _redis = None
    return _redis


async def close_redis():
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None


# ── Semantic Cache ────────────────────────────────────────────────────────────

def _cosine(a: list, b: list) -> float:
    va, vb = np.array(a), np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    return float(np.dot(va, vb) / denom) if denom > 0 else 0.0


async def search_cache(query_embedding: list) -> Optional[str]:
    """Return cached answer if a semantically similar query exists."""
    r = await get_redis()
    if not r:
        return None
    try:
        keys = await r.keys(f"{CACHE_PREFIX}*")
        for key in keys:
            raw = await r.get(key)
            if not raw:
                continue
            entry = json.loads(raw)
            sim = _cosine(query_embedding, entry["embedding"])
            if sim >= CACHE_THRESHOLD:
                return entry["answer"]
    except Exception as e:
        logger.error(f"Cache search error: {e}")
    return None


async def save_to_cache(query_embedding: list, answer: str):
    """Save a Q&A pair to semantic cache — never cache personal data."""
    r = await get_redis()
    if not r:
        return
    # Skip caching if answer looks personal
    personal_signals = ["ton compte", "votre réservation", "hashId", "montant", "solde"]
    if any(sig in answer.lower() for sig in personal_signals):
        return
    try:
        key = f"{CACHE_PREFIX}{hash(tuple(query_embedding[:8]))}"
        payload = json.dumps({"embedding": query_embedding, "answer": answer})
        await r.set(key, payload, ex=60 * 60 * 24)  # TTL 24h
    except Exception as e:
        logger.error(f"Cache save error: {e}")


# ── Session / History ─────────────────────────────────────────────────────────

async def get_history(user_id: str, max_turns: int = 10) -> list[dict]:
    """Retrieve last N conversation turns from Redis."""
    r = await get_redis()
    if not r:
        return []
    try:
        raw = await r.get(f"{SESSION_PREFIX}{user_id}")
        if not raw:
            return []
        history = json.loads(raw)
        return history[-max_turns:]
    except Exception:
        return []


async def save_history(user_id: str, role: str, content: str):
    """Append a message to the user's conversation history."""
    r = await get_redis()
    if not r:
        return
    try:
        key = f"{SESSION_PREFIX}{user_id}"
        raw = await r.get(key)
        history = json.loads(raw) if raw else []
        history.append({"role": role, "content": content})
        # Keep only last 20 messages
        history = history[-20:]
        await r.set(key, json.dumps(history), ex=SESSION_TTL)
    except Exception as e:
        logger.error(f"History save error: {e}")


async def set_history(user_id: str, history: list[dict]):
    """Overwrite the entire conversation history for a user."""
    r = await get_redis()
    if not r:
        return
    try:
        key = f"{SESSION_PREFIX}{user_id}"
        await r.set(key, json.dumps(history), ex=SESSION_TTL)
    except Exception as e:
        print(f"⚠️  History set error: {e}")


async def clear_history(user_id: str):
    r = await get_redis()
    if r:
        await r.delete(f"{SESSION_PREFIX}{user_id}")