"""
AgentForge – Document Ingestion Service
=========================================
Handles loading, chunking, deduplication, FAISS indexing, and
PostgreSQL persistence of knowledge-base documents.

Supports: raw text, PDF (via PyMuPDF), and URLs (via BeautifulSoup).
"""

import hashlib
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.backend.core.logging import get_logger
from agentforge.backend.database.models import Document
from agentforge.backend.vectorstore.faiss_store import FAISSVectorStore

logger = get_logger(__name__)

# Chunk configuration
CHUNK_SIZE = 800      # characters per chunk
CHUNK_OVERLAP = 150   # characters overlap between adjacent chunks


def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split text into overlapping chunks.
    Simple character-based splitter; swap for RecursiveCharacterTextSplitter
    if you need sentence-aware splitting.
    """
    if len(text) <= size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        start += size - overlap
    return chunks


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class IngestionService:
    """Orchestrates end-to-end document ingestion."""

    def __init__(self, db: AsyncSession, vector_store: FAISSVectorStore):
        self._db = db
        self._vs = vector_store

    async def ingest_text(
        self,
        title: str,
        source: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[uuid.UUID], int]:
        """
        Ingest a raw text document.
        Returns (list_of_document_ids, number_of_faiss_ids_assigned).
        """
        metadata = metadata or {}
        chunks = _chunk_text(content)
        doc_ids: List[uuid.UUID] = []
        texts_to_embed: List[str] = []
        metas_for_faiss: List[Dict[str, Any]] = []
        new_docs: List[Document] = []

        for idx, chunk in enumerate(chunks):
            chunk_hash = _content_hash(chunk)

            # Deduplication — skip already-indexed chunks
            existing = await self._db.execute(
                select(Document).where(
                    Document.content_hash == chunk_hash,
                    Document.chunk_index == idx,
                )
            )
            if existing.scalar_one_or_none():
                logger.debug("chunk_duplicate_skipped", hash=chunk_hash[:12])
                continue

            doc = Document(
                title=title,
                source=source,
                content=chunk,
                content_hash=chunk_hash,
                chunk_index=idx,
                chunk_total=len(chunks),
                metadata_=metadata,
                is_indexed=False,
            )
            self._db.add(doc)
            new_docs.append(doc)
            texts_to_embed.append(chunk)
            metas_for_faiss.append(
                {
                    "doc_id": str(doc.id),
                    "title": title,
                    "source": source,
                    "chunk_index": idx,
                    "content": chunk,
                    **metadata,
                }
            )

        if not texts_to_embed:
            logger.info("ingest_no_new_chunks", title=title)
            return [], 0

        # Flush to get IDs before FAISS indexing
        await self._db.flush()

        faiss_ids = await self._vs.add_documents(texts_to_embed, metas_for_faiss)

        # Write FAISS IDs back to the document rows
        for doc, fid in zip(new_docs, faiss_ids):
            doc.faiss_id = fid
            doc.is_indexed = True
            doc_ids.append(doc.id)

        await self._db.flush()
        logger.info(
            "ingest_complete",
            title=title,
            chunks=len(new_docs),
            faiss_vectors=len(faiss_ids),
        )
        return doc_ids, len(faiss_ids)

    async def load_sample_dataset(self) -> int:
        """
        Load bundled sample documents from sample_data/.
        Returns total chunks indexed.
        """
        # Resolve relative to this file's location so it works regardless of
        # which directory uvicorn / the process was launched from.
        sample_dir = Path(__file__).parent.parent.parent / "sample_data"
        if not sample_dir.exists():
            # Fall back to cwd-relative path (Docker / CI may mount it there)
            sample_dir = Path("sample_data")
        if not sample_dir.exists():
            logger.warning("sample_data_not_found", tried=str(sample_dir))
            return 0

        total = 0
        for txt_file in sample_dir.glob("*.txt"):
            content = txt_file.read_text(encoding="utf-8")
            _, count = await self.ingest_text(
                title=txt_file.stem.replace("_", " ").title(),
                source=str(txt_file),
                content=content,
                metadata={"dataset": "sample"},
            )
            total += count

        return total
