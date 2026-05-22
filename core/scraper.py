import httpx
from bs4 import BeautifulSoup
import asyncio
from typing import List, Dict
from core.preprocessing import clean_text
from database.models import RagChunk, KnowledgeSource
from rag.embedder import embed
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import update
import datetime
import logging

logger = logging.getLogger("naps-chatbot")

async def scrape_and_index(source_id: int, url: str, session: AsyncSession):
    """
    Scrapes a URL, cleans the text, and adds chunks to the DB.
    """
    try:
        # 1. Update status
        await session.execute(
            update(KnowledgeSource).where(KnowledgeSource.id == source_id).values(status="scraping")
        )
        await session.commit()

        # 2. Fetch content
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, follow_redirects=True)
            response.raise_for_status()
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.extract()
            
        # Get text
        text = soup.get_text(separator=' ')
        
        # 3. Process segments
        segments = [s.strip() for s in text.replace("\n", " ").split(".") if len(s.strip()) > 40]
        
        batch = []
        for s in segments:
            cleaned = clean_text(s)
            batch.append(RagChunk(
                content=s + ".",
                embedding=embed(cleaned),
                category="website",
                source=url,
                language="fr" # Default to FR for now
            ))
            
        # 4. Save chunks
        session.add_all(batch)
        
        # 5. Update source status
        await session.execute(
            update(KnowledgeSource).where(KnowledgeSource.id == source_id).values(
                status="active", 
                last_scrape=datetime.datetime.utcnow()
            )
        )
        await session.commit()
        return len(batch)

    except Exception as e:
        logger.error(f"Scraping error for {url}: {e}")
        await session.execute(
            update(KnowledgeSource).where(KnowledgeSource.id == source_id).values(status="error")
        )
        await session.commit()
        raise e
