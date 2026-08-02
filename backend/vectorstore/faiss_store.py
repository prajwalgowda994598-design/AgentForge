"""
AgentForge – FAISS Vector Store Service
=========================================
Manages document embedding, FAISS index construction, persistence, and
semantic retrieval.

Embedding providers:
  EMBEDDING_PROVIDER=openai  (default)
    → OpenAI text-embedding-3-small, 1536-dim
    → Requires OPENAI_API_KEY (separate from OpenRouter key)

  EMBEDDING_PROVIDER=local
    → sentence-transformers all-MiniLM-L6-v2, 384-dim
    → 100% free, no API key, runs on CPU
    → First run downloads ~90 MB model to ~/.cache
    → Install: pip install sentence-transformers
"""

import hashlib
import os
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional

import faiss
import numpy as np

from agentforge.backend.core.config import settings
from agentforge.backend.core.exceptions import VectorStoreError
from agentforge.backend.core.logging import get_logger

logger = get_logger(__name__)


# Module-level path constants — resolved lazily via properties so they can be
# patched in tests without changing the helper-function call sites below.
# Tests patch these names directly, e.g.:
#   patch("agentforge.backend.vectorstore.faiss_store.INDEX_FILE", ...)
INDEX_FILE: Optional[Path] = None      # set to None; resolved in _index_file()
METADATA_FILE: Optional[Path] = None  # set to None; resolved in _metadata_file()


def _index_file() -> Path:
    """Return INDEX_FILE if patched in tests, else resolve from settings."""
    if INDEX_FILE is not None:
        return INDEX_FILE
    return Path(settings.FAISS_INDEX_PATH) / "index.faiss"


def _metadata_file() -> Path:
    """Return METADATA_FILE if patched in tests, else resolve from settings."""
    if METADATA_FILE is not None:
        return METADATA_FILE
    return Path(settings.FAISS_INDEX_PATH) / "metadata.pkl"


def _build_embeddings():
    """
    Return the embedding model based on EMBEDDING_PROVIDER.

    openai → OpenAIEmbeddings (needs OPENAI_API_KEY, 1536-dim)
    local  → HuggingFaceEmbeddings via sentence-transformers (384-dim, free)
    """
    provider = settings.EMBEDDING_PROVIDER.lower()

    if provider == "local":
        try:
            # Use the current package — langchain_community version is deprecated
            from langchain_huggingface import HuggingFaceEmbeddings
            logger.info("embeddings_provider_local",
                        model="all-MiniLM-L6-v2",
                        note="First run downloads ~90MB model")
            return HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2",
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
        except ImportError:
            raise VectorStoreError(
                "EMBEDDING_PROVIDER=local requires langchain-huggingface. "
                "Run: pip install langchain-huggingface sentence-transformers"
            )

    # Default: OpenAI embeddings
    from langchain_openai import OpenAIEmbeddings
    if not settings.OPENAI_API_KEY:
        raise VectorStoreError(
            "EMBEDDING_PROVIDER=openai requires OPENAI_API_KEY to be set.\n"
            "Either:\n"
            "  1. Add OPENAI_API_KEY=sk-... to your .env file\n"
            "  2. Or set EMBEDDING_PROVIDER=local for a free local model"
        )
    logger.info("embeddings_provider_openai", model=settings.OPENAI_EMBEDDING_MODEL)
    return OpenAIEmbeddings(
        model=settings.OPENAI_EMBEDDING_MODEL,
        openai_api_key=settings.OPENAI_API_KEY,
    )


def _embedding_dimension() -> int:
    """Return the vector dimension for the active embedding provider."""
    if settings.EMBEDDING_PROVIDER.lower() == "local":
        return 384   # all-MiniLM-L6-v2 output size
    return 1536      # text-embedding-3-small output size


class FAISSVectorStore:
    """
    Thread-safe FAISS index wrapper with async-compatible interface.

    Metadata is stored in a parallel list: metadata[i] corresponds to the
    embedding at position i in the FAISS index.
    """

    def __init__(self):
        self._index: Optional[faiss.Index] = None
        self._metadata: List[Dict[str, Any]] = []
        self._embeddings = None   # lazy — built on first load_or_create()
        self._dimension  = _embedding_dimension()

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def _build_empty_index(self) -> faiss.Index:
        """Create an L2 flat index (exact search, suitable for <1M vectors)."""
        index = faiss.IndexFlatL2(self._dimension)
        # Wrap with an ID map so we can associate integer IDs
        return faiss.IndexIDMap(index)

    async def load_or_create(self) -> None:
        """
        Initialise the embedding model and load / create the FAISS index.
        Called once at startup by get_vector_store().
        """
        # Build embeddings lazily here so errors surface at startup, not import time
        if self._embeddings is None:
            self._embeddings = _build_embeddings()

        idx_file  = _index_file()
        meta_file = _metadata_file()
        Path(settings.FAISS_INDEX_PATH).mkdir(parents=True, exist_ok=True)
        if idx_file.exists() and meta_file.exists():
            try:
                self._index = faiss.read_index(str(idx_file))
                with open(meta_file, "rb") as f:
                    self._metadata = pickle.load(f)
                logger.info(
                    "faiss_index_loaded",
                    vectors=self._index.ntotal,
                    path=str(idx_file),
                )
            except Exception as exc:
                logger.warning("faiss_load_failed", error=str(exc), action="creating_fresh")
                self._index = self._build_empty_index()
                self._metadata = []
        else:
            self._index = self._build_empty_index()
            self._metadata = []
            logger.info("faiss_index_created", path=str(idx_file))

    def save(self) -> None:
        """Persist the index and metadata to disk."""
        if self._index is None:
            return
        faiss.write_index(self._index, str(_index_file()))
        with open(_metadata_file(), "wb") as f:
            pickle.dump(self._metadata, f)
        logger.debug("faiss_index_saved", vectors=self._index.ntotal)

    # ── Indexing ───────────────────────────────────────────────────────────────

    async def add_documents(
        self, texts: List[str], metadata_list: Optional[List[Dict[str, Any]]] = None
    ) -> List[int]:
        """
        Embed and add a list of text chunks to the FAISS index.
        Returns the assigned FAISS IDs.
        """
        if self._index is None:
            raise VectorStoreError("Index not initialised; call load_or_create() first")

        if not texts:
            return []

        metadata_list = metadata_list or [{} for _ in texts]
        if len(texts) != len(metadata_list):
            raise VectorStoreError("texts and metadata_list must have the same length")

        try:
            vectors = await self._embeddings.aembed_documents(texts)
        except Exception as exc:
            raise VectorStoreError(f"Embedding failed: {exc}") from exc

        vectors_np = np.array(vectors, dtype=np.float32)

        # Assign IDs starting after current max
        start_id = self._index.ntotal
        ids = np.arange(start_id, start_id + len(texts), dtype=np.int64)

        self._index.add_with_ids(vectors_np, ids)
        self._metadata.extend(metadata_list)

        self.save()
        logger.info("faiss_documents_added", count=len(texts), total=self._index.ntotal)
        return ids.tolist()

    # ── Retrieval ──────────────────────────────────────────────────────────────

    async def similarity_search(
        self, query: str, k: int = settings.FAISS_TOP_K
    ) -> List[Dict[str, Any]]:
        """
        Embed the query and return the top-k most similar document chunks
        with their metadata and L2 distance scores.
        """
        if self._index is None:
            raise VectorStoreError("Index not initialised")
        if self._index.ntotal == 0:
            logger.warning("faiss_search_empty_index")
            return []

        try:
            query_vector = await self._embeddings.aembed_query(query)
        except Exception as exc:
            raise VectorStoreError(f"Query embedding failed: {exc}") from exc

        query_np = np.array([query_vector], dtype=np.float32)
        actual_k = min(k, self._index.ntotal)

        distances, indices = self._index.search(query_np, actual_k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue
            meta = self._metadata[idx] if idx < len(self._metadata) else {}
            results.append(
                {
                    "faiss_id": int(idx),
                    "score": float(1 / (1 + dist)),  # normalise distance → similarity
                    "distance": float(dist),
                    **meta,
                }
            )

        logger.debug("faiss_search_complete", query_preview=query[:60], results=len(results))
        return results

    # ── Utilities ──────────────────────────────────────────────────────────────

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_vectors": self._index.ntotal if self._index else 0,
            "dimension": self._dimension,
            "index_type": type(self._index).__name__ if self._index else None,
            "index_path": str(_index_file()),
        }

    @staticmethod
    def content_hash(text: str) -> str:
        """SHA-256 hash of content for deduplication."""
        return hashlib.sha256(text.encode()).hexdigest()


# Module-level singleton
_vector_store: Optional[FAISSVectorStore] = None


async def get_vector_store() -> FAISSVectorStore:
    """Return the initialised singleton FAISS store."""
    global _vector_store
    if _vector_store is None:
        _vector_store = FAISSVectorStore()
        await _vector_store.load_or_create()
    return _vector_store
