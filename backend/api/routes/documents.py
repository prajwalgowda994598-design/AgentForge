"""
AgentForge – Document Ingestion API Routes
=============================================
Endpoints for loading documents into the knowledge base.

POST /documents           – Ingest raw text
GET  /documents/stats     – FAISS index statistics
POST /documents/load-sample – Load bundled sample dataset
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.backend.core.dependencies import get_db
from agentforge.backend.core.logging import get_logger
from agentforge.backend.models.schemas import DocumentIngestRequest, DocumentIngestResponse
from agentforge.backend.services.ingestion_service import IngestionService
from agentforge.backend.vectorstore.faiss_store import get_vector_store

router = APIRouter(prefix="/documents", tags=["documents"])
logger = get_logger(__name__)


@router.post(
    "",
    response_model=DocumentIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a document into the knowledge base",
)
async def ingest_document(
    body: DocumentIngestRequest,
    db: AsyncSession = Depends(get_db),
):
    vs = await get_vector_store()
    svc = IngestionService(db=db, vector_store=vs)
    doc_ids, faiss_count = await svc.ingest_text(
        title=body.title,
        source=body.source,
        content=body.content,
        metadata=body.metadata,
    )
    return DocumentIngestResponse(
        document_id=doc_ids[0] if doc_ids else None,
        chunks_created=len(doc_ids),
        faiss_indexed=faiss_count > 0,
        message=f"Ingested {len(doc_ids)} chunks, indexed {faiss_count} vectors.",
    )


@router.get("/stats", summary="FAISS vector store statistics")
async def get_vectorstore_stats():
    vs = await get_vector_store()
    return vs.get_stats()


@router.post(
    "/load-sample",
    summary="Load bundled sample dataset",
    status_code=status.HTTP_201_CREATED,
)
async def load_sample_data(db: AsyncSession = Depends(get_db)):
    vs = await get_vector_store()
    svc = IngestionService(db=db, vector_store=vs)
    total = await svc.load_sample_dataset()
    return {"message": f"Sample dataset loaded. {total} vectors indexed."}
