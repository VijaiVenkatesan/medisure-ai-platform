"""
ChromaDB vector store for policy document indexing and RAG retrieval.
Embedding strategy:
  - Local dev: sentence-transformers (all-MiniLM-L6-v2) — high quality
  - Render/cloud: chromadb default embedding function — no onnxruntime needed
"""
from __future__ import annotations
import hashlib
import os
from typing import Optional
import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings
from app.core.logging import get_logger
from app.models.schemas import InsuranceType, Country

logger = get_logger(__name__)

# Detect cloud environment — skip sentence-transformers on Render
_IS_CLOUD = (
    os.environ.get("RENDER") == "true"
    or os.environ.get("RAILWAY_ENVIRONMENT") is not None
    or os.environ.get("USE_DEFAULT_EMBEDDINGS") == "true"
)


def _get_embedding_function():
    """
    Return the best available embedding function for this environment.
    Cloud: chromadb's built-in (no extra deps).
    Local: sentence-transformers (better quality).
    """
    if not _IS_CLOUD:
        try:
            from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
            ef = SentenceTransformerEmbeddingFunction(
                model_name=settings.EMBEDDING_MODEL
            )
            logger.info(f"Using SentenceTransformer embeddings: {settings.EMBEDDING_MODEL}")
            return ef
        except Exception as e:
            logger.warning(f"SentenceTransformer unavailable: {e} — using default embeddings")

    # Fallback: chromadb's built-in embedding (all-MiniLM-L6-v2 via chromadb)
    try:
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
        logger.info("Using ChromaDB default embedding function (cloud mode)")
        return DefaultEmbeddingFunction()
    except Exception as e:
        logger.warning(f"DefaultEmbeddingFunction unavailable: {e} — using None (chromadb auto)")
        return None


class PolicyVectorStore:
    """
    ChromaDB-backed vector store for insurance policy documents.
    Supports semantic similarity search for policy eligibility checks.
    Uses environment-aware embedding: sentence-transformers locally,
    chromadb default function on Render/cloud (no onnxruntime needed).
    """

    def __init__(self):
        self._client: Optional[chromadb.Client] = None
        self._collection = None
        self._embedding_fn = None

    def _get_client(self) -> chromadb.Client:
        if self._client is None:
            os.makedirs(settings.CHROMA_PERSIST_DIR, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=settings.CHROMA_PERSIST_DIR,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )
            logger.info(f"ChromaDB initialized at {settings.CHROMA_PERSIST_DIR}")
        return self._client

    def _get_embedding_fn(self):
        if self._embedding_fn is None:
            self._embedding_fn = _get_embedding_function()
        return self._embedding_fn

    def _get_collection(self):
        if self._collection is None:
            client = self._get_client()
            ef = self._get_embedding_fn()
            kwargs = {
                "name": settings.CHROMA_COLLECTION_POLICIES,
                "metadata": {"hnsw:space": "cosine"},
            }
            if ef is not None:
                kwargs["embedding_function"] = ef
            self._collection = client.get_or_create_collection(**kwargs)
            logger.info(f"Using collection: {settings.CHROMA_COLLECTION_POLICIES}")
        return self._collection

    async def index_policy(
        self,
        policy_text: str,
        policy_name: str,
        insurance_type: InsuranceType,
        country: Country = Country.INDIA,
        company: Optional[str] = None,
        chunk_size: int = 400,
        chunk_overlap: int = 80,
    ) -> int:
        """
        Index a policy document into ChromaDB.
        Returns number of chunks indexed.
        """
        collection = self._get_collection()
        chunks = self._chunk_text(policy_text, chunk_size, chunk_overlap)

        if not chunks:
            logger.warning(f"No chunks generated for policy: {policy_name}")
            return 0

        # Prepare IDs and metadata
        policy_id = hashlib.sha256(policy_text.encode()).hexdigest()[:16]
        ids = [f"{policy_id}_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "policy_name": policy_name,
                "insurance_type": insurance_type.value if hasattr(insurance_type, 'value') else str(insurance_type),
                "country": country.value if hasattr(country, 'value') else str(country),
                "company": company or "Unknown",
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
            for i in range(len(chunks))
        ]

        # Upsert to collection — embedding function on collection handles vectors
        collection.upsert(
            ids=ids,
            documents=chunks,
            metadatas=metadatas,
        )

        logger.info(
            f"Policy indexed",
            extra={
                "extra_data": {
                    "policy_name": policy_name,
                    "chunks": len(chunks),
                    "insurance_type": str(insurance_type),
                    "country": str(country),
                }
            },
        )
        return len(chunks)

    async def search(
        self,
        query: str,
        insurance_type: Optional[str] = None,
        country: Optional[str] = None,
        top_k: int = 5,
    ) -> list[dict]:
        """
        Semantic search for relevant policy chunks.
        Returns list of {text, score, metadata} dicts.
        """
        collection = self._get_collection()

        if collection.count() == 0:
            logger.warning("Policy vector store is empty - no policies indexed")
            return []

        where: dict = {}
        if insurance_type:
            where["insurance_type"] = insurance_type
        if country:
            where["country"] = country

        # Use query_texts — collection's embedding function converts to vectors
        kwargs = {
            "query_texts": [query],
            "n_results": min(top_k, collection.count()),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where

        results = collection.query(**kwargs)

        output = []
        if results["documents"]:
            for doc, meta, dist in zip(
                results["documents"][0],
                results["metadatas"][0],
                results["distances"][0],
            ):
                similarity = 1.0 - dist
                output.append({
                    "text": doc,
                    "score": round(similarity, 4),
                    "policy_name": meta.get("policy_name", ""),
                    "insurance_type": meta.get("insurance_type", ""),
                    "country": meta.get("country", ""),
                    "company": meta.get("company", ""),
                })

        return sorted(output, key=lambda x: x["score"], reverse=True)

    def _chunk_text(self, text: str, chunk_size: int = 400, overlap: int = 80) -> list[str]:
        """
        Split text into overlapping chunks by CHARACTER count.
        chunk_size=400 chars gives ~60-80 words per chunk — ideal for RAG retrieval.
        Splits on sentence boundaries where possible to keep context intact.
        """
        text = text.strip()
        if not text:
            return []

        # First split into sentences / logical lines
        import re
        # Split on newlines and sentence endings
        sentences = re.split(r'(?<=[.!?])\s+|\n+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks = []
        current = ""

        for sentence in sentences:
            # If adding this sentence keeps us under chunk_size, add it
            if len(current) + len(sentence) + 1 <= chunk_size:
                current = (current + " " + sentence).strip()
            else:
                # Save current chunk if it has content
                if current:
                    chunks.append(current)
                # Start new chunk with overlap: carry last portion forward
                if len(current) > overlap:
                    # Take last `overlap` chars of previous chunk as context
                    overlap_text = current[-overlap:]
                    current = (overlap_text + " " + sentence).strip()
                else:
                    current = sentence

        # Don't forget the last chunk
        if current.strip():
            chunks.append(current.strip())

        # If a single sentence is longer than chunk_size, hard-split it
        final_chunks = []
        for chunk in chunks:
            if len(chunk) <= chunk_size * 1.5:
                final_chunks.append(chunk)
            else:
                # Hard split by chunk_size characters
                for i in range(0, len(chunk), chunk_size - overlap):
                    part = chunk[i:i + chunk_size]
                    if part.strip():
                        final_chunks.append(part.strip())

        return final_chunks

    def get_stats(self) -> dict:
        """Return vector store statistics."""
        try:
            collection = self._get_collection()
            return {
                "total_chunks": collection.count(),
                "collection_name": settings.CHROMA_COLLECTION_POLICIES,
            }
        except Exception as e:
            return {"error": str(e)}


# Singleton
_vector_store: Optional[PolicyVectorStore] = None


def get_vector_store() -> PolicyVectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = PolicyVectorStore()
    return _vector_store
