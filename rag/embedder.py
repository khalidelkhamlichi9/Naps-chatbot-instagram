from sentence_transformers import SentenceTransformer
import os

import logging

logger = logging.getLogger("naps-chatbot")

_model: SentenceTransformer | None = None


def load_embedder():
    """Lazy load the embedding model."""
    global _model
    if _model is not None:
        return _model
        
    model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    logger.info(f"Loading embedding model: {model_name}...")
    _model = SentenceTransformer(model_name)
    logger.info("Embedding model loaded successfully")
    return _model


def get_embedder() -> SentenceTransformer:
    if _model is None:
        return load_embedder()
    return _model


def embed(text: str) -> list[float]:
    """Embed a single string and return as list[float]."""
    return get_embedder().encode(text, normalize_embeddings=True).tolist()


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed multiple strings efficiently."""
    return get_embedder().encode(texts, normalize_embeddings=True).tolist()
