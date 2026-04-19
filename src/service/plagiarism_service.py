"""gRPC Service implementation for Plagiarism Detection."""

import logging, grpc
from typing import Iterator

from src import plagiarism_pb2, plagiarism_pb2_grpc

from src.core import (
    get_detector,
    get_document_manager,
    PlagiarismResult,
    PdfPlagiarismResult,
)
from src.storage import get_es_client

logger = logging.getLogger(__name__)


class PlagiarismService(plagiarism_pb2_grpc.PlagiarismServiceServicer):
    """gRPC service implementation for plagiarism detection."""
    
    def __init__(self):
        self.detector = get_detector()
        self.document_manager = get_document_manager()
        self.es_client = get_es_client()

    def CheckPlagiarism(
        self,
        request: plagiarism_pb2.CheckRequest,
        context: grpc.ServicerContext
        ) -> plagiarism_pb2.CheckResponse:
        """Check plagiarism between two documents."""
        try:
            logger.info(f"CheckPlagiarism request: {len(request.text)} chars")
            
            # Extract options (with safe defaults)
            options = request.options if request.HasField("options") else None
            min_similarity = None
            top_k = None
            include_ai = False  # Mặc định TẮT AI analysis để response nhanh
            exclude_docs = None
            
            if options:
                min_similarity = options.min_similarity if options.min_similarity > 0 else None
                top_k = options.top_k if options.top_k > 0 else None
                # Chỉ bật AI nếu client explicitly set = true
                if options.HasField("include_ai_analysis"):
                    include_ai = options.include_ai_analysis
                exclude_docs = list(options.exclude_docs) if options.exclude_docs else None
            
            # Run plagiarism check
            result = self.detector.check_plagiarism(
                text=request.text,
                min_similarity=min_similarity,
                top_k=top_k,
                include_ai_analysis=include_ai,
                exclude_doc_ids=exclude_docs,
            )
            
            return self._build_check_response(result)
        except Exception as e:
            logger.error(f"CheckPlagiarism error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return plagiarism_pb2.CheckResponse()
    
    def _build_check_response(self, result: PlagiarismResult) -> plagiarism_pb2.CheckResponse:
        # Convert severity string to enum
        severity_map = {
            "CRITICAL": plagiarism_pb2.Severity.CRITICAL,
            "HIGH": plagiarism_pb2.Severity.HIGH,
            "MEDIUM": plagiarism_pb2.Severity.MEDIUM,
            "LOW": plagiarism_pb2.Severity.LOW,
            "SAFE": plagiarism_pb2.Severity.SAFE,
        }
        
        # build matches
        matches = []
        for m in result.matches:
            matches.append(
                plagiarism_pb2.Match(
                    document_id=m.document_id,
                    document_title=m.document_title,
                    matched_text=m.matched_text,
                    input_text=m.input_text,
                    similarity_score=m.similarity_score,
                    position=plagiarism_pb2.Position(
                        start=m.position_start,
                        end=m.position_end,
                        chunk_index=m.chunk_index,
                    ),
                )
            )
        
        # Build chunk analysis
        chunk_analysis = []
        for c in result.chunk_analysis:
            chunk_analysis.append(
                plagiarism_pb2.ChunkAnalysis(
                    chunk_index=c.chunk_index,
                    text=c.text,
                    max_similarity=c.max_similarity,
                    status=severity_map.get(c.status, plagiarism_pb2.SAFE),
                    best_match_doc_id=c.best_match_doc_id or "",
                )
            )
        
        # Build metadata
        metadata = plagiarism_pb2.Metadata(
            processing_time_ms=result.processing_time_ms,
            chunks_analyzed=result.chunks_analyzed,
            documents_searched=result.documents_searched,
        )

        return plagiarism_pb2.CheckResponse(
            request_id=result.request_id,
            plagiarism_percentage=result.plagiarism_percentage,
            severity=severity_map.get(result.severity, plagiarism_pb2.SAFE),
            explanation=result.explanation,
            matches=matches,
            chunks=chunk_analysis,
            metadata=metadata,
        )
        
    def UploadDocument(self, request: plagiarism_pb2.UploadRequest, context: grpc.ServicerContext) -> plagiarism_pb2.UploadResponse:
        """Upload a document to the database."""
        try:
            logger.info(f"UploadDocument request: {request.title}")
            # Convert metadata
            metadata = dict(request.metadata) if request.metadata else {}
            # Upload document
            result = self.document_manager.upload_document(
                title=request.title,
                content=request.content,
                metadata=metadata,
                language=request.language or None,
            )
            return plagiarism_pb2.UploadResponse(
                document_id=result.document_id,
                title=result.title,
                chunks_created=result.chunks_created,
                message=result.message,
                success=result.success,
            )

        except Exception as e:
            logger.error(f"UploadDocument error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return plagiarism_pb2.UploadResponse(success=False, message=str(e))
        
    def BatchUpload(
        self,
        request_iterator: Iterator[plagiarism_pb2.UploadRequest],
        context: grpc.ServicerContext,
    ) -> plagiarism_pb2.BatchUploadResponse:
        """Batch upload documents using streaming."""
        try:
            results = []
            successful = 0
            failed = 0

            for request in request_iterator:
                metadata = dict(request.metadata) if request.metadata else {}

                result = self.document_manager.upload_document(
                    title=request.title,
                    content=request.content,
                    metadata=metadata,
                    language=request.language or None,
                )

                results.append(
                    plagiarism_pb2.UploadResult(
                        document_id=result.document_id,
                        title=result.title,
                        success=result.success,
                        error=result.error or "",
                    )
                )

                if result.success:
                    successful += 1
                else:
                    failed += 1

            return plagiarism_pb2.BatchUploadResponse(
                total_documents=len(results),
                successful=successful,
                failed=failed,
                results=results,
            )

        except Exception as e:
            logger.error(f"BatchUpload error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return plagiarism_pb2.BatchUploadResponse()

    def GetDocument(
        self,
        request: plagiarism_pb2.GetDocumentRequest,
        context: grpc.ServicerContext,
    ) -> plagiarism_pb2.GetDocumentResponse:
        """Get document by ID."""
        try:
            doc = self.document_manager.get_document(
                document_id=request.document_id,
                include_content=request.include_content,
                include_chunks=request.include_chunks,
            )

            if not doc:
                return plagiarism_pb2.GetDocumentResponse(found=False)

            # Build chunks if included
            chunks = []
            if request.include_chunks and "chunks" in doc:
                for c in doc["chunks"]:
                    chunks.append(
                        plagiarism_pb2.Chunk(
                            chunk_id=c.get("chunk_id", ""),
                            text=c.get("text", ""),
                            position=c.get("position", 0),
                            word_count=c.get("word_count", 0),
                        )
                    )

            document = plagiarism_pb2.Document(
                document_id=doc.get("document_id", ""),
                title=doc.get("title", ""),
                content=doc.get("content", "") if request.include_content else "",
                metadata=doc.get("metadata", {}),
                language=doc.get("language", ""),
                chunk_count=doc.get("chunk_count", 0),
                chunks=chunks,
                created_at=str(doc.get("created_at", "")),
                updated_at=str(doc.get("updated_at", "")),
            )

            return plagiarism_pb2.GetDocumentResponse(document=document, found=True)

        except Exception as e:
            logger.error(f"GetDocument error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return plagiarism_pb2.GetDocumentResponse(found=False)

    def DeleteDocument(
        self,
        request: plagiarism_pb2.DeleteDocumentRequest,
        context: grpc.ServicerContext,
    ) -> plagiarism_pb2.DeleteDocumentResponse:
        """Delete a document."""
        try:
            success = self.document_manager.delete_document(request.document_id)

            return plagiarism_pb2.DeleteDocumentResponse(
                success=success,
                message="Document deleted" if success else "Document not found",
            )

        except Exception as e:
            logger.error(f"DeleteDocument error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return plagiarism_pb2.DeleteDocumentResponse(
                success=False, message=str(e)
            )

    def SearchDocuments(
        self,
        request: plagiarism_pb2.SearchRequest,
        context: grpc.ServicerContext,
    ) -> plagiarism_pb2.SearchResponse:
        """Search documents."""
        try:
            filters = dict(request.filters) if request.filters else None
            limit = request.limit if request.limit > 0 else 10
            offset = request.offset if request.offset >= 0 else 0

            docs, total = self.document_manager.search_documents(
                query=request.query or None,
                filters=filters,
                limit=limit,
                offset=offset,
            )

            documents = []
            for doc in docs:
                documents.append(
                    plagiarism_pb2.DocumentSummary(
                        document_id=doc.get("document_id", ""),
                        title=doc.get("title", ""),
                        metadata=doc.get("metadata", {}),
                        language=doc.get("language", ""),
                        chunk_count=doc.get("chunk_count", 0),
                        created_at=str(doc.get("created_at", "")),
                    )
                )

            return plagiarism_pb2.SearchResponse(documents=documents, total=total)

        except Exception as e:
            logger.error(f"SearchDocuments error: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return plagiarism_pb2.SearchResponse()

    def HealthCheck(
        self,
        request: plagiarism_pb2.HealthCheckRequest,
        context: grpc.ServicerContext,
    ) -> plagiarism_pb2.HealthCheckResponse:
        """Check service health."""
        try:
            stats = self.document_manager.get_stats()

            components = {}

            # Elasticsearch health
            es_health = stats.get("es_health", {})
            components["elasticsearch"] = plagiarism_pb2.ComponentHealth(
                healthy=es_health.get("healthy", False),
                message=es_health.get("status", es_health.get("error", "Unknown")),
            )

            # Ollama health
            ollama_health = stats.get("ollama_health", {})
            components["ollama"] = plagiarism_pb2.ComponentHealth(
                healthy=ollama_health.get("healthy", False),
                message="Available" if ollama_health.get("healthy") else ollama_health.get("error", "Unknown"),
            )

            overall_healthy = all(c.healthy for c in components.values())

            return plagiarism_pb2.HealthCheckResponse(
                healthy=overall_healthy,
                components=components,
            )

        except Exception as e:
            logger.error(f"HealthCheck error: {e}")
            return plagiarism_pb2.HealthCheckResponse(healthy=False)

    def IndexPdfFromMinio(
        self,
        request: plagiarism_pb2.IndexDocumentFromMinioRequest,
        context: grpc.ServicerContext,
    ) -> plagiarism_pb2.IndexDocumentFromMinioResponse:
        """Index a PDF file from MinIO bucket."""
        try:
            logger.info(
                f"IndexPdfFromMinio: {request.bucket_name}/{request.object_path}"
            )

            # Convert metadata
            metadata = dict(request.metadata) if request.metadata else {}

            # Call document manager
            result = self.document_manager.upload_pdf_from_minio(
                bucket_name=request.bucket_name,
                object_path=request.object_path,
                document_id=request.document_id or None,
                title=request.title or None,
                metadata=metadata,
                language=request.language or None,
            )

            if not result.success:
                return plagiarism_pb2.IndexDocumentFromMinioResponse(
                    success=False,
                    document_id=result.document_id,
                    error_message=result.error_message,
                )

            # Build chunk info
            chunks = []
            for chunk_info in result.chunks_info:
                chunks.append(
                    plagiarism_pb2.PdfChunkInfo(
                        chunk_id=chunk_info["chunk_id"],
                        section_title=chunk_info["section_title"],
                        content_preview=chunk_info["content_preview"],
                        element_type=chunk_info["element_type"],
                        position=chunk_info["position"],
                        word_count=chunk_info["word_count"],
                    )
                )

            # Build processing metadata
            proc_meta = result.processing_metadata
            processing_metadata = plagiarism_pb2.PdfProcessingMetadata(
                total_pages=proc_meta.get("total_pages", 0),
                total_elements=proc_meta.get("total_elements", 0),
                total_chunks=proc_meta.get("total_chunks", 0),
                processing_time_ms=proc_meta.get("processing_time_ms", 0),
                pdf_title=proc_meta.get("pdf_title", ""),
                pdf_author=proc_meta.get("pdf_author", ""),
            )

            return plagiarism_pb2.IndexDocumentFromMinioResponse(
                success=True,
                document_id=result.document_id,
                title=result.title,
                total_chunks=result.total_chunks,
                chunks=chunks,
                processing_metadata=processing_metadata,
            )

        except Exception as e:
            logger.error(f"IndexPdfFromMinio error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return plagiarism_pb2.IndexDocumentFromMinioResponse(
                success=False,
                error_message=str(e),
            )

    def CheckPdfFromMinio(
        self,
        request: plagiarism_pb2.CheckPdfFromMinioRequest,
        context: grpc.ServicerContext,
    ) -> plagiarism_pb2.CheckPdfFromMinioResponse:
        """Check a PDF file from MinIO for plagiarism."""
        try:
            logger.info(
                f"CheckPdfFromMinio: {request.bucket_name}/{request.object_path}"
            )

            # Extract options
            options = request.options if request.HasField("options") else None
            min_similarity = None
            top_k = None
            include_ai = False
            exclude_docs = None

            if options:
                min_similarity = options.min_similarity if options.min_similarity > 0 else None
                top_k = options.top_k if options.top_k > 0 else None
                if options.HasField("include_ai_analysis"):
                    include_ai = options.include_ai_analysis
                exclude_docs = list(options.exclude_docs) if options.exclude_docs else None

            # Call detector
            result = self.detector.check_pdf_from_minio(
                bucket_name=request.bucket_name,
                object_path=request.object_path,
                min_similarity=min_similarity,
                top_k=top_k,
                include_ai_analysis=include_ai,
                exclude_doc_ids=exclude_docs,
            )

            return self._build_pdf_check_response(result)

        except Exception as e:
            logger.error(f"CheckPdfFromMinio error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return plagiarism_pb2.CheckPdfFromMinioResponse(
                success=False,
                error_message=str(e),
            )

    def _build_pdf_check_response(
        self, result: PdfPlagiarismResult
    ) -> plagiarism_pb2.CheckPdfFromMinioResponse:
        """Build gRPC response from PdfPlagiarismResult."""
        # Convert severity string to enum
        severity_map = {
            "SAFE": plagiarism_pb2.SAFE,
            "LOW": plagiarism_pb2.LOW,
            "MEDIUM": plagiarism_pb2.MEDIUM,
            "HIGH": plagiarism_pb2.HIGH,
            "CRITICAL": plagiarism_pb2.CRITICAL,
        }

        # Build matches
        matches = []
        for m in result.matches:
            matches.append(
                plagiarism_pb2.Match(
                    document_id=m.document_id,
                    document_title=m.document_title,
                    matched_text=m.matched_text,
                    input_text=m.input_text,
                    similarity_score=m.similarity_score,
                    position=plagiarism_pb2.Position(
                        start_char=m.position_start,
                        end_char=m.position_end,
                        start_word=0,
                        end_word=0,
                    ),
                )
            )

        # Build chunk analysis
        chunks = []
        for c in result.chunk_analysis:
            chunks.append(
                plagiarism_pb2.ChunkAnalysis(
                    chunk_index=c.chunk_index,
                    text=c.text,
                    similarity_score=c.max_similarity,
                    is_plagiarized=c.max_similarity > 0.8,
                    source_document_id=c.best_match_doc_id or "",
                    source_text=c.best_match_text or "",
                )
            )

        # Build metadata
        metadata = plagiarism_pb2.PdfCheckMetadata(
            processing_time_ms=result.metadata.processing_time_ms,
            pdf_extraction_time_ms=result.metadata.pdf_extraction_time_ms,
            embedding_time_ms=result.metadata.embedding_time_ms,
            search_time_ms=result.metadata.search_time_ms,
            total_pages=result.metadata.total_pages,
            total_chunks=result.metadata.total_chunks,
            chunks_analyzed=result.metadata.chunks_analyzed,
            documents_searched=result.metadata.documents_searched,
            model_used=result.metadata.model_used,
        )

        return plagiarism_pb2.CheckPdfFromMinioResponse(
            success=result.success,
            request_id=result.request_id,
            document_title=result.document_title,
            plagiarism_percentage=result.plagiarism_percentage,
            severity=severity_map.get(result.severity, plagiarism_pb2.SAFE),
            explanation=result.explanation,
            matches=matches,
            chunks=chunks,
            metadata=metadata,
            error_message=result.error_message,
        )

            
            