import os
import importlib
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv

# Load .env variables so DATABASE_URL is available
load_dotenv()

# Force registers direct strings backend
# Ila kan os.getenv fih relative path wla sqlite standard, gha n-m9adoh absolute absolute
ENV_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:////app/data/naps_chatbot.db")


# 🔥 FIX: Ila kant 3ndna gha 3 d l-slashes (///) w machi relative path (///./), n-rj3ohom 4 (////) bach y-welli absolute path d Linux
if "sqlite+aiosqlite:///" in ENV_URL and not ENV_URL.startswith("sqlite+aiosqlite:////") and not ENV_URL.startswith("sqlite+aiosqlite:///./"):
    DATABASE_URL = ENV_URL.replace("sqlite+aiosqlite:///", "sqlite+aiosqlite:////")
else:
    DATABASE_URL = ENV_URL

print(f"[DB CONFIG] Standardized Database URL: {DATABASE_URL}")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

from database.models import Base

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

get_session = get_db

async def init_db():
    # Get the raw path by removing the SQLAlchemy prefix correctly
    if "sqlite+aiosqlite:////" in DATABASE_URL:
        db_path = DATABASE_URL.replace("sqlite+aiosqlite:////", "/")
    elif "sqlite+aiosqlite:///" in DATABASE_URL:
        db_path = DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    else:
        db_path = DATABASE_URL
    
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        print(f"[DB INIT] Creating directory: {db_dir}")
        os.makedirs(db_dir, exist_ok=True)

    # Force register models 
    possible_model_modules = ["models", "database.models", "app.models"]
    for module_name in possible_model_modules:
        try:
            importlib.import_module(module_name)
        except ImportError:
            continue

    try:
        print(f"[DB INIT] Sync creating tables on absolute path: {db_path}")
        from sqlalchemy import create_engine
        sync_url = DATABASE_URL.replace("sqlite+aiosqlite://", "sqlite://")
        sync_engine = create_engine(sync_url)
        Base.metadata.create_all(sync_engine)
        sync_engine.dispose()
        print("[DB INIT] Sync database generation successful.")
    except Exception as e:
        print(f"[DB INIT] Sync error: {e}. Trying async fallback...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)