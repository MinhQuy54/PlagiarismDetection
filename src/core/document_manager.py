import logging 
from typing import Optional, Generator
from dataclasses import dataclass
from uuid import uuid4
from datetime import datetime

from src.config.settings import get_settings
from src.storage.elasticsearch import get_es_client, DocumentChunk, DocumentData
from src.embedding.ollama_embed import get_ollama_client
from src.storage.minio_client import get_minio_client
from src.core.chunker import get_chunker
from src.core.processor import get_pdf_processor

logger = logging.getLogger(__name__)


@dataclass
class UploadResult:
    """Result of document upload."""

    document_id: str
    title: str
    chunks_created: int
    success: bool
    message: str
    error: Optional[str] = None


@dataclass
class BatchUploadResult:
    """Result of batch upload."""

    total_documents: int
    successful: int
    failed: int
    results: list[UploadResult]


@dataclass
class PdfUploadResult:
    """Result of PDF upload from MinIO."""

    document_id: str
    title: str
    success: bool
    total_chunks: int
    chunks_info: list[dict]  # Info about each chunk
    processing_metadata: dict  # PDF processing stats
    error_message: str = ""


class DocumentManager:
    def __init__(self):
        self.settings = get_settings()
        self.es_client = get_es_client()
        self.ollama_client = get_ollama_client()
        self.chunker = get_chunker()
        self.minio_client = get_minio_client()
        self.pdf_processor = get_pdf_processor()
    
    
    def upload_document(
        self, 
        title: str,
        content: str,
        metadata: Optional[dict[str, str]] = None,
        language: Optional[str] = None,
        document_id: Optional[str] = None,
    ) -> UploadResult:
        
        try:
            doc_id = document_id or str(uuid4())
            
            # Detect language if not provided
            if not language or language == 'auto':
                language = self.chunker.detect_language(content)
                
            # Chunk the content
            
            chunks = self.chunker.chunk_text(content)
            
            if not chunks:
                return UploadResult(
                    document_id=doc_id,
                    title=title,
                    chunks_created=0,
                    success=False,
                    message="Document content too short to process",
                )
                
            # Generate embeddings for chunks
            chunk_texts = [chunk.text for chunk in chunks]
            embeddings = self.ollama_client.embed_batch(chunk_texts)
            
            # Create document chunks with embeddings
            doc_chunks = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                doc_chunks.append(
                    DocumentChunk(
                        chunk_id=f"{doc_id}_chunk_{i}",
                        text=chunk.text,
                        embedding=embedding,
                        position=chunk.position,
                        word_count=chunk.word_count,
                    )
                    
                )
            # Create document data
            doc_data = DocumentData(
                document_id=doc_id,
                title=title,
                content=content,
                chunks=doc_chunks,
                language=language,
                metadata=metadata or {},
                created_at=datetime.utcnow(),
            )
            
            # Index document
            success = self.es_client.index_document(doc_data)
            
            if success:
                logger.info(f"Uploaded document: {doc_id} ({len(doc_chunks)} chunks)")
                return UploadResult(
                    document_id=doc_id,
                    title=title,
                    chunks_created=len(doc_chunks),
                    success=True,
                    message=f"Successfully uploaded with {len(doc_chunks)} chunks",
                )
            else:
                logger.error(f"Failed to index document: {doc_id}")
                return UploadResult(
                    document_id=doc_id,
                    title=title,
                    chunks_created=0,
                    success=False,
                    message="Failed to index document",
                )
        except Exception as e:
            logger.error(f"Failed to upload document: {e}")
            return UploadResult(
                document_id=document_id or "",
                title=title,
                chunks_created=0,
                success=False,
                message="Upload failed",
                error=str(e),
            ) 
    
    
    def batch_upload(
        self,
        documents: list[dict],
        on_progress: Optional[callable] = None,
    ) -> BatchUploadResult:
        """Upload multiple documents.
        
        Args:
            documents: List of documents to upload.
            on_progress: Callback function to report progress.
        
        Returns:
            BatchUploadResult with upload results.
        """
        results = []
        successful = 0
        failed = 0
        
        for i, doc in enumerate(documents):
            result = self.upload_document(
                title=doc.get("title", f"Document {i+1}"),
                content=doc.get("content", ""),
                metadata=doc.get("metadata"),
                language=doc.get("language"),
                document_id=doc.get("document_id"),
            )
            
            results.append(result)
            
            if result.success:
                successful += 1
            else: failed += 1

            if on_progress:
                on_progress(i + 1, len(documents), result)
        
        return BatchUploadResult(
            total_documents=len(documents),
            successful=successful,
            failed=failed,
            results=results,
        )
    def batch_upload_stream(
        self,
        documents: Generator[dict, None, None],
    ) -> Generator[UploadResult, None, None]:
        """Stream upload documents one by one.

        Args:
            documents: Generator of document dicts

        Yields:
            UploadResult for each document
        """
        for doc in documents:
            result = self.upload_document(
                title=doc.get("title", "Untitled"),
                content=doc.get("content", ""),
                metadata=doc.get("metadata"),
                language=doc.get("language"),
            )
            yield result
    
    def get_document(
        self,
        document_id: str,
        include_content: bool = False,
        include_chunks: bool = False,
    ) -> Optional[dict]:
        """Get document by ID.

        Args:
            document_id: Document ID
            include_content: Include full content
            include_chunks: Include chunk details

        Returns:
            Document dict or None
        """
        doc = self.es_client.get_document(document_id, include_chunks=include_chunks)

        if doc and not include_content:
            doc.pop("content", None)

        return doc

    def delete_document(self, document_id: str) -> bool:
        """Delete document and its chunks.

        Args:
            document_id: Document ID to delete

        Returns:
            True if deleted, False otherwise
        """
        return self.es_client.delete_document(document_id)

    def search_documents(
        self,
        query: Optional[str] = None,
        filters: Optional[dict[str, str]] = None,
        limit: int = 10,
        offset: int = 0,
    ) -> tuple[list[dict], int]:
        """Search documents.

        Args:
            query: Text query
            filters: Metadata filters
            limit: Max results
            offset: Pagination offset

        Returns:
            Tuple of (documents list, total count)
        """
        return self.es_client.search_documents(
            query=query,
            filters=filters,
            limit=limit,
            offset=offset,
        )

    def get_stats(self) -> dict:
        """Get system statistics."""
        return {
            "total_documents": self.es_client.get_document_count(),
            "es_health": self.es_client.health_check(),
            "ollama_health": self.ollama_client.health_check(),
        }
    
    def upload_pdf_form_minio(
        self,
        bucket_name: str,
        object_path: str,
        document_id: Optional[str] = None,
        title: Optional[str] = None,
        metadata: Optional[dict[str, str]] = None,
        language: Optional[str] = None,
    ) -> PdfUploadResult:
        """
        Upload PDF from MinIO, extract content with titles, and index to Elasticsearch.

        Args:
            bucket_name: MinIO bucket name
            object_path: Path to PDF file in bucket
            document_id: Optional custom document ID
            title: Optional document title (extracted from PDF if not provided)
            metadata: Optional metadata dict
            language: Language code (auto-detect if not provided)

        Returns:
            PdfUploadResult with processing details
        """
        import os, tempfile
        
        doc_id = document_id or str(uuid4())
        
        try:
            # Check if object exists
            if not self.minio_client.object_exists(bucket_name, object_path):
                return PdfUploadResult(
                    document_id=doc_id,
                    title="",
                    success=False,
                    total_chunks=0,
                    chunks_info=[],
                    processing_metadata={},
                    error_message=f"Object not found: {bucket_name}/{object_path}",
                )
                
            # Download PDF to temp file
            local_path = self.minio_client.download_file(bucket_name, object_path)
            if not local_path:
                return PdfUploadResult(
                    document_id=doc_id,
                    title="",
                    success=False,
                    total_chunks=0,
                    chunks_info=[],
                    processing_metadata={},
                    error_message="Failed to download file from MinIO",
                )
            
            try:
                # Process PDF
                pdf_result = self.pdf_processor.process_pdf(
                    pdf_path=local_path,
                    document_id=doc_id,
                )
                if not pdf_result.success:
                    return PdfUploadResult(
                        document_id=doc_id,
                       title="",
                        success=False,
                        total_chunks=0,
                        chunks_info=[],
                        processing_metadata={},
                        error_message=pdf_result.error_message,
                    )

                if not pdf_result.chunks:
                    return PdfUploadResult(
                        document_id=doc_id,
                        title=pdf_result.document_title,
                        success=False,
                        total_chunks=0,
                        chunks_info=[],
                        processing_metadata={},
                        error_message="No content extracted from PDF",
                    )
                
                # Use provided title or extracted title
                doc_title = title or pdf_result.document_title

                # Generate embeddings for all chunks
                chunk_texts = [chunk.text for chunk in pdf_result.chunks]
                embeddings = self.ollama_client.embed_batch(chunk_texts)

                # Detect language from first chunk if not provided
                if not language or language == "auto":
                    language = self.chunker.detect_language(chunk_texts[0])

                # Create document chunks with embeddings
                doc_chunks = []
                for chunk, embedding in zip(pdf_result.chunks, embeddings):
                    doc_chunks.append(
                        DocumentChunk(
                            chunk_id=chunk.chunk_id,
                            text=chunk.text,
                            embedding=embedding,
                            position=chunk.position,
                            word_count=chunk.word_count,
                        )
                    )

                # Combine all chunk texts for full content
                full_content = "\n\n".join(
                    f"## {chunk.section_title}\n{chunk.text}"
                    for chunk in pdf_result.chunks
                )
                
                # Build metadata
                doc_metadata = metadata or {}
                doc_metadata["source_bucket"] = bucket_name
                doc_metadata["source_path"] = object_path
                doc_metadata["pdf_pages"] = str(pdf_result.total_pages)
                
                # Create document data
                doc_data = DocumentData(
                    document_id=doc_id,
                    title=doc_title,
                    content=full_content,
                    chunks=doc_chunks,
                    language=language,
                    metadata=doc_metadata,
                    created_at=datetime.utcnow(),
                )

                # Index document
                success = self.es_client.index_document(doc_data)

                if not success:
                    return PdfUploadResult(
                        document_id=doc_id,
                        title=doc_title,
                        success=False,
                        total_chunks=0,
                        chunks_info=[],
                        processing_metadata={},
                        error_message="Failed to index document in Elasticsearch",
                    )

                # Build chunks info for response
                chunks_info = [
                    {
                        "chunk_id": chunk.chunk_id,
                        "section_title": chunk.section_title,
                        "content_preview": chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text,
                        "element_type": chunk.element_type,
                        "position": chunk.position,
                        "word_count": chunk.word_count,
                    }
                    for chunk in pdf_result.chunks
                ]

                logger.info(
                    f"Uploaded PDF from MinIO: {doc_id} ({len(doc_chunks)} chunks) "
                    f"from {bucket_name}/{object_path}"
                )

                return PdfUploadResult(
                    document_id=doc_id,
                    title=doc_title,
                    success=True,
                    total_chunks=len(doc_chunks),
                    chunks_info=chunks_info,
                    processing_metadata={
                        "total_pages": pdf_result.total_pages,
                        "total_elements": pdf_result.total_elements,
                        "total_chunks": len(pdf_result.chunks),
                        "processing_time_ms": pdf_result.processing_time_ms,
                        "pdf_title": pdf_result.document_title,
                        "pdf_author": pdf_result.pdf_metadata.get("author", ""),
                    },
                )

            finally:
                # Clean up temp file
                if local_path and os.path.exists(local_path):
                    os.remove(local_path)

        except Exception as e:
            logger.error(f"Failed to upload PDF from MinIO: {e}", exc_info=True)
            return PdfUploadResult(
                document_id=doc_id,
                title="",
                success=False,
                total_chunks=0,
                chunks_info=[],
                processing_metadata={},
                error_message=str(e),
            )


# Singleton instance
_document_manager: Optional[DocumentManager] = None


def get_document_manager() -> DocumentManager:
    """Get singleton document manager instance."""
    global _document_manager
    if _document_manager is None:
        _document_manager = DocumentManager()
    return _document_manager
