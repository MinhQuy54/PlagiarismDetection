"""Elasticsearch client wrapper for plagiarism detection."""

import logging
from typing import Any, Optional
from datetime import datetime

from elasticsearch import Elasticsearch, NotFoundError, BadRequestError
from pydantic import BaseModel

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class DocumentChunk(BaseModel):
    """A chunk of document with embedding."""
    chunk_id: str
    text: str
    embedding: list[float]
    position: int
    word_count: int


class DocumentData(BaseModel):
    """Document data for storage."""
    document_id: str
    title: str
    content: str
    chunks: list[DocumentChunk]
    language: str
    metadata: dict[str, str] = {}
    created_at: Optional[datetime] = None


class SearchResult(BaseModel):
    """Search result from vector search."""
    document_id: str
    chunk_id: str
    document_title: str
    matched_text: str
    similarity_score: float
    position: int
    metadata: dict[str, str] = {}


class ElasticsearchClient:
    """Elasticsearch client for document storage and vector search."""

    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[Elasticsearch] = None

    @property
    def client(self) -> Elasticsearch:
        """Get or create Elasticsearch client."""
        if self._client is None:
            # Always use basic_auth if user and password are provided
            auth = None
            if self.settings.es_user and self.settings.es_password:
                auth = (self.settings.es_user, self.settings.es_password)
                logger.info(f"Using ES authentication with user: {self.settings.es_user}")

            self._client = Elasticsearch(
                hosts=[self.settings.es_url],
                basic_auth=auth,
                verify_certs=False,
                request_timeout=30,
            )
        return self._client

    @property
    def index_name(self) -> str:
        """Get index name."""
        return self.settings.es_index

    def health_check(self) -> dict[str, Any]:
        """Check Elasticsearch health."""
        try:
            info = self.client.info()
            health = self.client.cluster.health()
            return {
                "healthy": True,
                "version": info["version"]["number"],
                "cluster_name": health["cluster_name"],
                "status": health["status"],
            }
        except Exception as e:
            logger.error(f"ES health check failed: {e}")
            return {"healthy": False, "error": str(e)}

    def create_index(self, force: bool = False) -> bool:
        """Create index with proper mappings for vector search."""
        if self.client.indices.exists(index=self.index_name):
            if force:
                logger.warning(f"Deleting existing index: {self.index_name}")
                self.client.indices.delete(index=self.index_name)
            else:
                logger.info(f"Index {self.index_name} already exists")
                return True

        mappings = {
            "mappings": {
                "properties": {
                    "document_id": {"type": "keyword"},
                    "title": {
                        "type": "text",
                        "analyzer": "standard",
                        "fields": {"keyword": {"type": "keyword"}},
                    },
                    "content": {"type": "text", "analyzer": "standard"},
                    "language": {"type": "keyword"},
                    "metadata": {"type": "object", "enabled": True},
                    "created_at": {"type": "date"},
                    "updated_at": {"type": "date"},
                    "chunk_count": {"type": "integer"},
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
            },
        }

        try:
            self.client.indices.create(index=self.index_name, body=mappings)
            logger.info(f"Created index: {self.index_name}")

            # Create chunks index with vector search
            self._create_chunks_index(force)
            return True
        except BadRequestError as e:
            logger.error(f"Failed to create index: {e}")
            return False

    def _create_chunks_index(self, force: bool = False) -> bool:
        """Create chunks index for vector search."""
        chunks_index = f"{self.index_name}_chunks"

        if self.client.indices.exists(index=chunks_index):
            if force:
                self.client.indices.delete(index=chunks_index)
            else:
                return True

        mappings = {
            "mappings": {
                "properties": {
                    "chunk_id": {"type": "keyword"},
                    "document_id": {"type": "keyword"},
                    "document_title": {"type": "text"},
                    "text": {"type": "text", "analyzer": "standard"},
                    "embedding": {
                        "type": "dense_vector",
                        "dims": self.settings.embedding_dims,
                        "index": True,
                        "similarity": "cosine",
                    },
                    "position": {"type": "integer"},
                    "word_count": {"type": "integer"},
                    "metadata": {"type": "object"},
                    "created_at": {"type": "date"},
                }
            },
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
            },
        }

        try:
            self.client.indices.create(index=chunks_index, body=mappings)
            logger.info(f"Created chunks index: {chunks_index}")
            return True
        except BadRequestError as e:
            logger.error(f"Failed to create chunks index: {e}")
            return False

    # ==================== CRUD Operations ====================

    def index_document(self, document: DocumentData) -> bool:
        """Index a document and its chunks."""
        try:
            # Index main document
            doc_body = {
                "document_id": document.document_id,
                "title": document.title,
                "content": document.content,
                "language": document.language,
                "metadata": document.metadata,
                "chunk_count": len(document.chunks),
                "created_at": document.created_at or datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }

            self.client.index(
                index=self.index_name,
                id=document.document_id,
                document=doc_body,
            )

            # Index chunks with embeddings
            chunks_index = f"{self.index_name}_chunks"
            for chunk in document.chunks:
                chunk_body = {
                    "chunk_id": chunk.chunk_id,
                    "document_id": document.document_id,
                    "document_title": document.title,
                    "text": chunk.text,
                    "embedding": chunk.embedding,
                    "position": chunk.position,
                    "word_count": chunk.word_count,
                    "metadata": document.metadata,
                    "created_at": datetime.utcnow(),
                }
                self.client.index(
                    index=chunks_index,
                    id=chunk.chunk_id,
                    document=chunk_body,
                )

            # Refresh to make documents searchable immediately
            self.client.indices.refresh(index=self.index_name)
            self.client.indices.refresh(index=chunks_index)

            logger.info(
                f"Indexed document {document.document_id} with {len(document.chunks)} chunks"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to index document: {e}")
            return False

    def get_document(
        self, document_id: str, include_chunks: bool = False
    ) -> Optional[dict[str, Any]]:
        """Get document by ID."""
        try:
            result = self.client.get(index=self.index_name, id=document_id)
            doc = result["_source"]

            if include_chunks:
                chunks = self._get_document_chunks(document_id)
                doc["chunks"] = chunks

            return doc
        except NotFoundError:
            return None
        except Exception as e:
            logger.error(f"Failed to get document: {e}")
            return None

    def _get_document_chunks(self, document_id: str) -> list[dict]:
        """Get all chunks for a document."""
        chunks_index = f"{self.index_name}_chunks"
        try:
            result = self.client.search(
                index=chunks_index,
                query={"term": {"document_id": document_id}},
                size=1000,
                sort=[{"position": "asc"}],
            )
            return [hit["_source"] for hit in result["hits"]["hits"]]
        except Exception as e:
            logger.error(f"Failed to get chunks: {e}")
            return []

    def delete_document(self, document_id: str) -> bool:
        """Delete document and its chunks."""
        try:
            # Delete main document
            self.client.delete(index=self.index_name, id=document_id)

            # Delete chunks
            chunks_index = f"{self.index_name}_chunks"
            self.client.delete_by_query(
                index=chunks_index,
                query={"term": {"document_id": document_id}},
            )

            logger.info(f"Deleted document: {document_id}")
            return True
        except NotFoundError:
            logger.warning(f"Document not found: {document_id}")
            return False
        except Exception as e:
            logger.error(f"Failed to delete document: {e}")
            return False

    def search_documents(
        self,
        query: Optional[str] = None,
        filters: Optional[dict[str, str]] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """Search documents by text query and/or filters."""
        must_clauses = []

        if query:
            must_clauses.append(
                {
                    "multi_match": {
                        "query": query,
                        "fields": ["title^2", "content"],
                    }
                }
            )

        if filters:
            for key, value in filters.items():
                must_clauses.append({"term": {f"metadata.{key}": value}})

        search_query = {"bool": {"must": must_clauses}} if must_clauses else {"match_all": {}}

        try:
            result = self.client.search(
                index=self.index_name,
                query=search_query,
                from_=offset,
                size=limit,
                sort=[{"created_at": "desc"}],
            )

            docs = [hit["_source"] for hit in result["hits"]["hits"]]
            total = result["hits"]["total"]["value"]
            return docs, total
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return [], 0

    # ==================== Vector Search ====================

    def vector_search(
        self,
        embedding: list[float],
        top_k: int = 10,
        min_score: float = 0.5,
        exclude_doc_ids: Optional[list[str]] = None,
    ) -> list[SearchResult]:
        """Search for similar chunks using vector similarity."""
        chunks_index = f"{self.index_name}_chunks"

        # Build filter for exclusions
        filter_clause = None
        if exclude_doc_ids:
            filter_clause = {
                "bool": {"must_not": [{"terms": {"document_id": exclude_doc_ids}}]}
            }

        try:
            # kNN search
            knn_query = {
                "field": "embedding",
                "query_vector": embedding,
                "k": top_k,
                "num_candidates": top_k * 10,
            }

            if filter_clause:
                knn_query["filter"] = filter_clause

            result = self.client.search(
                index=chunks_index,
                knn=knn_query,
                size=top_k,
                _source=["chunk_id", "document_id", "document_title", "text", "position", "metadata"],
            )

            results = []
            for hit in result["hits"]["hits"]:
                score = hit["_score"]
                # Elasticsearch returns scores, convert to similarity
                # For cosine similarity, score is already between 0 and 1
                if score >= min_score:
                    source = hit["_source"]
                    results.append(
                        SearchResult(
                            document_id=source["document_id"],
                            chunk_id=source["chunk_id"],
                            document_title=source.get("document_title", ""),
                            matched_text=source["text"],
                            similarity_score=score,
                            position=source.get("position", 0),
                            metadata=source.get("metadata", {}),
                        )
                    )

            # Group by document and limit results per source
            return self._limit_results_per_source(
                results, self.settings.max_results_per_source
            )

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    def _limit_results_per_source(
        self, results: list[SearchResult], max_per_source: int
    ) -> list[SearchResult]:
        """Limit results per source document to avoid bias."""
        doc_counts: dict[str, int] = {}
        filtered_results = []

        for result in results:
            doc_id = result.document_id
            if doc_counts.get(doc_id, 0) < max_per_source:
                filtered_results.append(result)
                doc_counts[doc_id] = doc_counts.get(doc_id, 0) + 1

        return filtered_results

    def get_document_count(self) -> int:
        """Get total document count."""
        try:
            result = self.client.count(index=self.index_name)
            return result["count"]
        except Exception as e:
            logger.error(f"Failed to get count: {e}")
            return 0

    def close(self):
        """Close the client connection."""
        if self._client:
            self._client.close()
            self._client = None


# Singleton instance
_es_client: Optional[ElasticsearchClient] = None


def get_es_client() -> ElasticsearchClient:
    """Get singleton ES client instance."""
    global _es_client
    if _es_client is None:
        _es_client = ElasticsearchClient()
    return _es_client
