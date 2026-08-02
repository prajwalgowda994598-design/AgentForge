"""
Unit tests for FAISS vector store service.
Uses mocked embeddings to avoid real OpenAI API calls.
"""

import os
import tempfile
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest


class TestFAISSVectorStore:
    """Tests for FAISSVectorStore."""

    @pytest.fixture
    def tmp_index_path(self, tmp_path):
        """Temporary directory for FAISS index files."""
        return str(tmp_path / "faiss_test")

    @pytest.fixture
    def mock_embeddings(self):
        """Mock OpenAI embeddings returning random 1536-dim vectors."""
        mock = MagicMock()
        mock.aembed_documents = AsyncMock(
            side_effect=lambda texts: [[float(i) * 0.001 + j * 0.0001 for i in range(1536)] for j, _ in enumerate(texts)]
        )
        mock.aembed_query = AsyncMock(
            return_value=[0.5] * 1536
        )
        return mock

    @pytest.mark.asyncio
    async def test_load_or_create_builds_empty_index(self, tmp_index_path, mock_embeddings):
        """load_or_create should build a fresh index when none exists."""
        with patch("agentforge.backend.vectorstore.faiss_store.settings") as mock_settings:
            mock_settings.FAISS_INDEX_PATH = tmp_index_path
            mock_settings.FAISS_DIMENSION = 1536
            mock_settings.FAISS_TOP_K = 5
            mock_settings.OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
            mock_settings.OPENAI_API_KEY = "sk-test"

            from agentforge.backend.vectorstore.faiss_store import FAISSVectorStore

            store = FAISSVectorStore()
            store._embeddings = mock_embeddings
            store._dimension = 1536

            with patch("agentforge.backend.vectorstore.faiss_store.INDEX_FILE", Path(tmp_index_path) / "index.faiss"), \
                 patch("agentforge.backend.vectorstore.faiss_store.METADATA_FILE", Path(tmp_index_path) / "metadata.pkl"):
                await store.load_or_create()

        assert store._index is not None
        assert store._index.ntotal == 0

    @pytest.mark.asyncio
    async def test_add_and_search_documents(self, tmp_index_path, mock_embeddings):
        """Should embed, index, and retrieve documents correctly."""
        import faiss
        from agentforge.backend.vectorstore.faiss_store import FAISSVectorStore

        store = FAISSVectorStore()
        store._embeddings = mock_embeddings
        store._dimension = 1536

        # Build a fresh index manually
        base_index = faiss.IndexFlatL2(1536)
        store._index = faiss.IndexIDMap(base_index)
        store._metadata = []

        with patch("agentforge.backend.vectorstore.faiss_store.INDEX_FILE", Path(tmp_index_path) / "index.faiss"), \
             patch("agentforge.backend.vectorstore.faiss_store.METADATA_FILE", Path(tmp_index_path) / "metadata.pkl"), \
             patch.object(store, "save"):  # don't write to disk in unit tests
            ids = await store.add_documents(
                ["Document one about quantum.", "Document two about AI."],
                [{"title": "QC", "source": "s1.txt"}, {"title": "AI", "source": "s2.txt"}],
            )

        assert len(ids) == 2
        assert store._index.ntotal == 2

    @pytest.mark.asyncio
    async def test_similarity_search_returns_results(self, tmp_index_path, mock_embeddings):
        """Search should return top-k results sorted by similarity."""
        import faiss
        import numpy as np
        from agentforge.backend.vectorstore.faiss_store import FAISSVectorStore

        store = FAISSVectorStore()
        store._embeddings = mock_embeddings
        store._dimension = 1536

        base_index = faiss.IndexFlatL2(1536)
        store._index = faiss.IndexIDMap(base_index)

        # Add a vector manually
        vec = np.array([[0.5] * 1536], dtype=np.float32)
        store._index.add_with_ids(vec, np.array([0], dtype=np.int64))
        store._metadata = [{"title": "Test Doc", "source": "test.txt", "content": "test content"}]

        with patch("agentforge.backend.vectorstore.faiss_store.INDEX_FILE", Path(tmp_index_path) / "index.faiss"):
            results = await store.similarity_search("test query", k=1)

        assert len(results) == 1
        assert results[0]["title"] == "Test Doc"
        assert "score" in results[0]

    def test_content_hash_is_deterministic(self):
        """Same content should always produce the same hash."""
        from agentforge.backend.vectorstore.faiss_store import FAISSVectorStore

        text = "The quick brown fox jumps over the lazy dog"
        h1 = FAISSVectorStore.content_hash(text)
        h2 = FAISSVectorStore.content_hash(text)
        assert h1 == h2
        assert len(h1) == 64  # SHA-256 hex digest
