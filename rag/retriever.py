import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import RagChunk
from rag.embedder import embed
from llm.deepseek import call_llm_short
import os
import logging

logger = logging.getLogger("naps-chatbot")

RAG_TOP_K        = int(os.getenv("RAG_TOP_K", "5"))
RAG_RERANK_TOP_K = int(os.getenv("RAG_RERANK_TOP_K", "3"))


def _cosine_scores(query_vec: list, chunk_vecs: list) -> np.ndarray:
    q = np.array(query_vec)
    C = np.array(chunk_vecs)
    scores = C @ q  # normalized vectors → dot = cosine
    return scores


async def retrieve(query: str, session: AsyncSession) -> list[dict]:
    """
    Full RAG retrieval pipeline:
    1. Embed query
    2. Cosine search → top-5
    3. LLM reranking → top-3
    Returns list of dicts with keys: content, category, score
    """
    query_vec = embed(query)

    # ── 1. Fetch all chunks + embeddings ──────────────────────────────────────
    result = await session.execute(select(RagChunk))
    all_chunks = result.scalars().all()

    if not all_chunks:
        return []

    # Filter website vs others
    web_chunks   = [c for c in all_chunks if c.category == "website"]
    other_chunks = [c for c in all_chunks if c.category != "website"]

    # ── 2. Strategy: Website First ──────────────────────────────────────────
    def get_top_k(target_chunks, k):
        if not target_chunks: return []
        v   = [c.embedding for c in target_chunks]
        s   = _cosine_scores(query_vec, v)
        idx = np.argsort(s)[::-1][:k]
        return [
            {"id": target_chunks[i].id, "content": target_chunks[i].content, "category": target_chunks[i].category, "score": float(s[i])}
            for i in idx if s[i] > 0.35 # Slightly higher threshold for website
        ]

    candidates = get_top_k(web_chunks, RAG_TOP_K)

    # If no good website match, fallback to others
    if not candidates:
        candidates = get_top_k(other_chunks, RAG_TOP_K)

    if not candidates:
        return []

    # ── 3. Performance Optimization: Skip reranking if confidence is high ──────
    if candidates[0]["score"] > 0.82:
        return candidates[:RAG_RERANK_TOP_K]

    # ── 4. LLM Reranking ──────────────────────────────────────────────────────
    reranked = await _rerank(query, candidates)
    return reranked[:RAG_RERANK_TOP_K]


async def _rerank(query: str, candidates: list[dict]) -> list[dict]:
    """Ask DeepSeek to pick the most relevant chunk IDs."""
    numbered = "\n".join(
        f"[{i+1}] {c['content'][:200]}" for i, c in enumerate(candidates)
    )
    prompt = (
        f"Question: {query}\n\n"
        f"Chunks:\n{numbered}\n\n"
        f"Return ONLY a JSON array of the {RAG_RERANK_TOP_K} most relevant chunk numbers, "
        f"ordered by relevance. Example: [2, 1, 4]. No explanation."
    )
    try:
        raw = await call_llm_short(prompt, max_tokens=50)
        import json, re
        match = re.search(r"\[[\d,\s]+\]", raw)
        if match:
            indices = json.loads(match.group())
            reranked = []
            for idx in indices:
                if 1 <= idx <= len(candidates):
                    reranked.append(candidates[idx - 1])
            if reranked:
                return reranked
    except Exception as e:
        logger.error(f"Reranking failed, using cosine order: {e}")
    return candidates


def build_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a context string for the LLM."""
    if not chunks:
        return ""
    parts = []
    for c in chunks:
        # Use uppercase for better visibility
        category = c.get("category", "Général").upper()
        parts.append(f"SOURCE [{category}]:\n{c['content']}")
    return "\n\n---\n\n".join(parts)
