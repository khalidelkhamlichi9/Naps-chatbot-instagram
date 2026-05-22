from sqlalchemy import Column, Integer, String, Text, Boolean, Float, JSON, TIMESTAMP, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func

Base = declarative_base()


class UploadedDocument(Base):
    """Tracks files uploaded by the admin."""
    __tablename__ = "uploaded_documents"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    filename   = Column(String(255), nullable=False)
    category   = Column(String(100), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # Relationship to chunks
    chunks = relationship("RagChunk", back_populates="document", cascade="all, delete-orphan")


class KnowledgeSource(Base):
    """Tracks websites to be scraped."""
    __tablename__ = "knowledge_sources"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    url         = Column(String(500), nullable=False, unique=True)
    name        = Column(String(100), nullable=True)
    status      = Column(String(20), default="pending")  # pending | scraping | active | error
    last_scrape = Column(TIMESTAMP, nullable=True)
    created_at  = Column(TIMESTAMP, server_default=func.now())


class RagChunk(Base):
    """Knowledge base chunks with precomputed embeddings."""
    __tablename__ = "rag_chunks"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    content     = Column(Text, nullable=False)
    embedding   = Column(JSON, nullable=False)        # list[float] stored as JSON
    source      = Column(String(255), default="manual")
    document_id = Column(Integer, ForeignKey("uploaded_documents.id", ondelete="CASCADE"), nullable=True)
    category    = Column(String(100), nullable=True)  # tpe | ecommerce | carte | entreprise | support
    language    = Column(String(10), default="fr")
    created_at  = Column(TIMESTAMP, server_default=func.now())
    updated_at  = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    # Relationship to document
    document = relationship("UploadedDocument", back_populates="chunks")


class SystemPrompt(Base):
    """Versioned system prompts with rollback support."""
    __tablename__ = "system_prompts"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    language   = Column(String(10), default="fr", index=True)
    content    = Column(Text, nullable=False)
    created_by = Column(String(100), default="admin")
    created_at = Column(TIMESTAMP, server_default=func.now())
    is_active  = Column(Boolean, default=False)
    version    = Column(Integer, nullable=False, default=1)
    note       = Column(String(255), nullable=True)


class Conversation(Base):
    """Conversation log for analytics — no message content in production."""
    __tablename__ = "conversations"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    user_id       = Column(String(100), nullable=False, index=True)
    platform      = Column(String(50), default="instagram")
    language      = Column(String(20), nullable=True)
    latency_ms    = Column(Float, nullable=True)
    cache_hit     = Column(Boolean, default=False)
    created_at    = Column(TIMESTAMP, server_default=func.now())
