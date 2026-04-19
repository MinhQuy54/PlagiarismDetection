"""Main plagiarism detection logic."""

import logging
import os
import time
from typing import Optional
from dataclasses import dataclass, field
from uuid import uuid4

from src.config.settings import get_settings
from src.storage.elasticsearch import get_es_client, SearchResult
from src.storage.minio_client import get_minio_client
from src.embedding.ollama_embed import get_ollama_client
from src.core.chunker import get_chunker, TextChunk
from src.core.analyzer import get_analyzer, AnalysisResult
from src.core.lexical_matcher import calculate_combined_similarity
from src.core.processor import get_pdf_processor

logger = logging.getLogger(__name__)


@dataclass
class ChunkAnalysisResult:
    """Analysis result for a single chunk."""

    chunk_index: int
    text: str
    max_similarity: float
    status: str
    best_match_doc_id: Optional[str] = None
    best_match_title: Optional[str] = None
    matches: list[SearchResult] = field(default_factory=list)


@dataclass
class PlagiarismMatch:
    """A plagiarism match result."""

    document_id: str
    document_title: str
    matched_text: str
    input_text: str
    similarity_score: float
    position_start: int
    position_end: int
    chunk_index: int  # Input chunk index
    matched_chunk_id: str = ""  # Matched chunk ID from database


@dataclass
class PlagiarismResult:
    """Complete plagiarism check result."""

    request_id: str
    plagiarism_percentage: float
    severity: str
    explanation: str
    matches: list[PlagiarismMatch]
    chunk_analysis: list[ChunkAnalysisResult]
    processing_time_ms: int
    chunks_analyzed: int
    documents_searched: int
    ai_analysis: Optional[AnalysisResult] = None


@dataclass
class PdfCheckMetadata:
    """Metadata for PDF plagiarism check."""

    processing_time_ms: int
    pdf_extraction_time_ms: int
    embedding_time_ms: int
    search_time_ms: int
    total_pages: int
    total_chunks: int
    chunks_analyzed: int
    documents_searched: int
    model_used: str = ""


@dataclass
class PdfPlagiarismResult:
    """Complete PDF plagiarism check result."""

    success: bool
    request_id: str
    document_title: str
    plagiarism_percentage: float
    severity: str
    explanation: str
    matches: list[PlagiarismMatch]
    chunk_analysis: list[ChunkAnalysisResult]
    metadata: PdfCheckMetadata
    error_message: str = ""


@dataclass
class PdfTextChunk:
    """Wrapper for PDF chunk to match TextChunk interface."""

    text: str
    word_count: int
    position: int
    start_char: int = 0
    end_char: int = 0


class PlagiarismDetector:
    """Main plagiarism detection engine."""

    def __init__(self):
        self.settings = get_settings()
        self.es_client = get_es_client()
        self.ollama_client = get_ollama_client()
        self.chunker = get_chunker()
        self.analyzer = get_analyzer()
        self.minio_client = get_minio_client()
        self.pdf_processor = get_pdf_processor()

    def check_plagiarism(
        self,
        text: str,
        min_similarity: Optional[float] = None,
        top_k: Optional[int] = None,
        include_ai_analysis: bool = True,
        exclude_doc_ids: Optional[list[str]] = None,
    ) -> PlagiarismResult:
        """Check text for plagiarism.

        Args:
            text: Text to check
            min_similarity: Minimum similarity threshold (default from settings)
            top_k: Number of results per chunk (default from settings)
            include_ai_analysis: Whether to use AI for final analysis
            exclude_doc_ids: Document IDs to exclude from search

        Returns:
            PlagiarismResult with detailed analysis
        """
        start_time = time.time()
        request_id = str(uuid4())

        min_similarity = min_similarity or self.settings.min_score_threshold
        top_k = top_k or self.settings.top_k_results

        # Step 1: Chunk the text
        chunks = self.chunker.chunk_text(text)
        logger.info(f"Split text into {len(chunks)} chunks")

        if not chunks:
            return self._empty_result(request_id, start_time)

        # Step 2: Generate embeddings for all chunks
        chunk_texts = [chunk.text for chunk in chunks]
        embeddings = self.ollama_client.embed_batch(chunk_texts)

        # Step 3: Search for similar chunks in database
        all_matches: list[PlagiarismMatch] = []
        chunk_results: list[ChunkAnalysisResult] = []

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            # Vector search
            search_results = self.es_client.vector_search(
                embedding=embedding,
                top_k=top_k,
                min_score=min_similarity,
                exclude_doc_ids=exclude_doc_ids,
            )

            # Process results for this chunk
            chunk_analysis = self._analyze_chunk(i, chunk, search_results)
            chunk_results.append(chunk_analysis)

            # Add matches
            for result in search_results:
                all_matches.append(
                    PlagiarismMatch(
                        document_id=result.document_id,
                        document_title=result.document_title,
                        matched_text=result.matched_text,
                        input_text=chunk.text,
                        similarity_score=result.similarity_score,
                        position_start=chunk.start_char,
                        position_end=chunk.end_char,
                        chunk_index=i,
                        matched_chunk_id=result.chunk_id,
                    )
                )

        # Step 4: Calculate base plagiarism percentage
        base_percentage = self._calculate_base_percentage(chunks, chunk_results)

        # Step 5: AI-enhanced analysis (optional)
        ai_result = None
        if include_ai_analysis and all_matches:
            ai_result = self._run_ai_analysis(text, all_matches, base_percentage)
            final_percentage = ai_result.plagiarism_percentage
            severity = ai_result.severity
            explanation = ai_result.explanation
        else:
            final_percentage = base_percentage
            severity = self.settings.get_severity(base_percentage / 100)
            explanation = self._generate_explanation(base_percentage, len(all_matches))

        # Step 6: Deduplicate and sort matches
        unique_matches = self._deduplicate_matches(all_matches)

        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)

        return PlagiarismResult(
            request_id=request_id,
            plagiarism_percentage=final_percentage,
            severity=severity,
            explanation=explanation,
            matches=unique_matches,
            chunk_analysis=chunk_results,
            processing_time_ms=processing_time_ms,
            chunks_analyzed=len(chunks),
            documents_searched=self.es_client.get_document_count(),
            ai_analysis=ai_result,
        )

    def _analyze_chunk(
        self,
        chunk_index: int,
        chunk: TextChunk,
        search_results: list[SearchResult],
    ) -> ChunkAnalysisResult:
        """Analyze a single chunk's search results with combined scoring."""
        if not search_results:
            return ChunkAnalysisResult(
                chunk_index=chunk_index,
                text=chunk.text,
                max_similarity=0.0,
                status="SAFE",
                matches=[],
            )

        # Recalculate similarity using combined semantic + lexical scoring
        combined_results = []
        for result in search_results:
            combined_score, _ = calculate_combined_similarity(
                semantic_score=result.similarity_score,
                input_text=chunk.text,
                matched_text=result.matched_text,
            )
            # Update the result's similarity score with combined score
            result.similarity_score = combined_score
            combined_results.append(result)

        # Find best match after recalculation
        max_result = max(combined_results, key=lambda x: x.similarity_score)
        max_similarity = max_result.similarity_score
        status = self.settings.get_severity(max_similarity)

        return ChunkAnalysisResult(
            chunk_index=chunk_index,
            text=chunk.text,
            max_similarity=max_similarity,
            status=status,
            best_match_doc_id=max_result.document_id,
            best_match_title=max_result.document_title,
            matches=combined_results,
        )

    def _calculate_base_percentage(
        self,
        chunks: list[TextChunk],
        chunk_results: list[ChunkAnalysisResult],
    ) -> float:
        """Calculate base plagiarism percentage based on plagiarized text ratio.

        This calculates the percentage of text (by word count) that has
        similarity score >= threshold, weighted by the actual similarity score.

        For chunks above threshold: counts as (word_count * similarity)
        For chunks below threshold: counts as 0

        This gives a more accurate representation of how much text is plagiarized.
        """
        if not chunks or not chunk_results:
            return 0.0

        total_words = sum(chunk.word_count for chunk in chunks)
        if total_words == 0:
            return 0.0

        # Use the low threshold as minimum for considering a chunk as "plagiarized"
        plagiarism_threshold = self.settings.similarity_low  # 0.50 by default

        # Calculate plagiarized word count weighted by similarity
        # Chunks above threshold contribute: word_count * similarity
        # Chunks below threshold contribute: 0
        plagiarized_weighted = 0.0
        for i, result in enumerate(chunk_results):
            if result.max_similarity >= plagiarism_threshold:
                # Weight by similarity - higher similarity = more plagiarized
                plagiarized_weighted += chunks[i].word_count * result.max_similarity

        return (plagiarized_weighted / total_words) * 100

    def _run_ai_analysis(
        self,
        text: str,
        matches: list[PlagiarismMatch],
        base_percentage: float,
    ) -> AnalysisResult:
        """Run AI-enhanced analysis."""
        # Convert matches to dict format for analyzer
        match_dicts = [
            {
                "document_title": m.document_title,
                "matched_text": m.matched_text,
                "similarity_score": m.similarity_score,
            }
            for m in matches[:10]  # Limit to top 10 for AI
        ]

        return self.analyzer.analyze(text, match_dicts, base_percentage)

    def _generate_explanation(
        self, percentage: float, match_count: int
    ) -> str:
        """Generate explanation without AI."""
        if percentage >= 95:
            return f"Phát hiện đạo văn nghiêm trọng. Tìm thấy {match_count} đoạn trùng khớp cao với tài liệu trong database."
        elif percentage >= 85:
            return f"Phát hiện đạo văn mức cao. {match_count} đoạn văn có độ tương đồng cao."
        elif percentage >= 70:
            return f"Nghi ngờ đạo văn. {match_count} đoạn văn có nội dung tương tự với các nguồn khác."
        elif percentage >= 50:
            return f"Có {match_count} đoạn có thể trùng ý tưởng với các tài liệu khác."
        else:
            return "Văn bản an toàn, không phát hiện đạo văn đáng kể."

    def _deduplicate_matches(
        self, matches: list[PlagiarismMatch]
    ) -> list[PlagiarismMatch]:
        """Remove duplicate matches and sort by similarity.

        Deduplicates by matched_chunk_id to ensure each matched chunk
        from the database appears only once, keeping the highest similarity.
        """
        seen = set()
        unique = []

        # Sort by similarity descending
        sorted_matches = sorted(
            matches, key=lambda x: x.similarity_score, reverse=True
        )

        for match in sorted_matches:
            # Use matched_chunk_id as key to deduplicate by database chunk
            # This allows multiple chunks from same document if they are different chunks
            key = match.matched_chunk_id
            if key not in seen:
                seen.add(key)
                unique.append(match)

        return unique

    def _empty_result(
        self, request_id: str, start_time: float
    ) -> PlagiarismResult:
        """Generate empty result for empty/invalid input."""
        return PlagiarismResult(
            request_id=request_id,
            plagiarism_percentage=0.0,
            severity="SAFE",
            explanation="Văn bản quá ngắn hoặc không hợp lệ để phân tích.",
            matches=[],
            chunk_analysis=[],
            processing_time_ms=int((time.time() - start_time) * 1000),
            chunks_analyzed=0,
            documents_searched=0,
        )

    def _create_error_pdf_result(
        self,
        request_id: str,
        start_time: float,
        error_message: str,
        document_title: str = "",
        pdf_extraction_time_ms: int = 0,
        total_pages: int = 0,
    ) -> PdfPlagiarismResult:
        """Create error PdfPlagiarismResult with common defaults."""
        return PdfPlagiarismResult(
            success=False,
            request_id=request_id,
            document_title=document_title,
            plagiarism_percentage=0.0,
            severity="SAFE",
            explanation="",
            matches=[],
            chunk_analysis=[],
            metadata=PdfCheckMetadata(
                processing_time_ms=int((time.time() - start_time) * 1000),
                pdf_extraction_time_ms=pdf_extraction_time_ms,
                embedding_time_ms=0,
                search_time_ms=0,
                total_pages=total_pages,
                total_chunks=0,
                chunks_analyzed=0,
                documents_searched=0,
            ),
            error_message=error_message,
        )

    def _search_and_analyze_pdf_chunks(
        self,
        pdf_chunks: list,
        embeddings: list[list[float]],
        top_k: int,
        min_similarity: float,
        exclude_doc_ids: Optional[list[str]],
    ) -> tuple[list[PlagiarismMatch], list[ChunkAnalysisResult]]:
        """Search for similar chunks and analyze results.

        Returns:
            Tuple of (all_matches, chunk_results)
        """
        all_matches: list[PlagiarismMatch] = []
        chunk_results: list[ChunkAnalysisResult] = []

        # Calculate cumulative character positions
        cumulative_char = 0

        for i, (pdf_chunk, embedding) in enumerate(zip(pdf_chunks, embeddings)):
            # Vector search
            search_results = self.es_client.vector_search(
                embedding=embedding,
                top_k=top_k,
                min_score=min_similarity,
                exclude_doc_ids=exclude_doc_ids,
            )

            # Create wrapper for analysis with actual character positions
            chunk_obj = PdfTextChunk(
                text=pdf_chunk.text,
                word_count=pdf_chunk.word_count,
                position=pdf_chunk.position,
                start_char=cumulative_char,
                end_char=cumulative_char + len(pdf_chunk.text),
            )
            cumulative_char += len(pdf_chunk.text) + 1  # +1 for separator

            # Analyze chunk
            chunk_analysis = self._analyze_chunk(i, chunk_obj, search_results)
            chunk_results.append(chunk_analysis)

            # Collect matches
            for result in search_results:
                all_matches.append(
                    PlagiarismMatch(
                        document_id=result.document_id,
                        document_title=result.document_title,
                        matched_text=result.matched_text,
                        input_text=pdf_chunk.text,
                        similarity_score=result.similarity_score,
                        position_start=chunk_obj.start_char,
                        position_end=chunk_obj.end_char,
                        chunk_index=i,
                        matched_chunk_id=result.chunk_id,
                    )
                )

        return all_matches, chunk_results

    def check_pdf_from_minio(
        self,
        bucket_name: str,
        object_path: str,
        min_similarity: Optional[float] = None,
        top_k: Optional[int] = None,
        include_ai_analysis: bool = False,
        exclude_doc_ids: Optional[list[str]] = None,
    ) -> PdfPlagiarismResult:
        """Check a PDF file from MinIO for plagiarism.

        Args:
            bucket_name: MinIO bucket name
            object_path: Path to PDF file in bucket
            min_similarity: Minimum similarity threshold
            top_k: Number of results per chunk
            include_ai_analysis: Whether to use AI for analysis
            exclude_doc_ids: Document IDs to exclude

        Returns:
            PdfPlagiarismResult with detailed analysis
        """
        start_time = time.time()
        request_id = str(uuid4())
        local_path = None

        min_similarity = min_similarity or self.settings.min_score_threshold
        top_k = top_k or self.settings.top_k_results

        try:
            # Validate object exists
            if not self.minio_client.object_exists(bucket_name, object_path):
                return self._create_error_pdf_result(
                    request_id, start_time,
                    f"Object not found: {bucket_name}/{object_path}"
                )

            # Download PDF
            local_path = self.minio_client.download_file(bucket_name, object_path)
            if not local_path:
                return self._create_error_pdf_result(
                    request_id, start_time,
                    "Failed to download file from MinIO"
                )

            # Step 1: Process PDF
            pdf_start = time.time()
            pdf_result = self.pdf_processor.process_pdf(
                pdf_path=local_path,
                document_id=request_id,
            )
            pdf_extraction_time = int((time.time() - pdf_start) * 1000)

            if not pdf_result.success:
                return self._create_error_pdf_result(
                    request_id, start_time,
                    pdf_result.error_message,
                    pdf_extraction_time_ms=pdf_extraction_time,
                )

            if not pdf_result.chunks:
                return self._create_error_pdf_result(
                    request_id, start_time,
                    "No content extracted from PDF",
                    document_title=pdf_result.document_title,
                    pdf_extraction_time_ms=pdf_extraction_time,
                    total_pages=pdf_result.total_pages,
                )

            logger.info(f"Extracted {len(pdf_result.chunks)} chunks from PDF")

            # Step 2: Generate embeddings
            embed_start = time.time()
            chunk_texts = [chunk.text for chunk in pdf_result.chunks]
            embeddings = self.ollama_client.embed_batch(chunk_texts)
            embedding_time = int((time.time() - embed_start) * 1000)
            logger.info(f"Generated {len(embeddings)} embeddings")

            # Step 3: Search and analyze chunks
            search_start = time.time()
            all_matches, chunk_results = self._search_and_analyze_pdf_chunks(
                pdf_chunks=pdf_result.chunks,
                embeddings=embeddings,
                top_k=top_k,
                min_similarity=min_similarity,
                exclude_doc_ids=exclude_doc_ids,
            )
            search_time = int((time.time() - search_start) * 1000)

            # Step 4: Calculate plagiarism percentage
            pdf_text_chunks = [
                PdfTextChunk(c.text, c.word_count, c.position)
                for c in pdf_result.chunks
            ]
            base_percentage = self._calculate_base_percentage(pdf_text_chunks, chunk_results)

            # Step 5: AI analysis or generate explanation
            full_text = "\n\n".join(chunk_texts)
            if include_ai_analysis and all_matches:
                ai_result = self._run_ai_analysis(full_text, all_matches, base_percentage)
                final_percentage = ai_result.plagiarism_percentage
                severity = ai_result.severity
                explanation = ai_result.explanation
            else:
                final_percentage = base_percentage
                severity = self.settings.get_severity(base_percentage / 100)
                explanation = self._generate_explanation(base_percentage, len(all_matches))

            # Build result
            return PdfPlagiarismResult(
                success=True,
                request_id=request_id,
                document_title=pdf_result.document_title,
                plagiarism_percentage=final_percentage,
                severity=severity,
                explanation=explanation,
                matches=self._deduplicate_matches(all_matches),
                chunk_analysis=chunk_results,
                metadata=PdfCheckMetadata(
                    processing_time_ms=int((time.time() - start_time) * 1000),
                    pdf_extraction_time_ms=pdf_extraction_time,
                    embedding_time_ms=embedding_time,
                    search_time_ms=search_time,
                    total_pages=pdf_result.total_pages,
                    total_chunks=len(pdf_result.chunks),
                    chunks_analyzed=len(chunk_results),
                    documents_searched=self.es_client.get_document_count(),
                    model_used=self.settings.ollama_embed_model,
                ),
            )

        except Exception as e:
            logger.error(f"Failed to check PDF plagiarism: {e}", exc_info=True)
            return self._create_error_pdf_result(request_id, start_time, str(e))

        finally:
            # Clean up temp file
            if local_path and os.path.exists(local_path):
                os.remove(local_path)


# Singleton instance
_detector: Optional[PlagiarismDetector] = None


def get_detector() -> PlagiarismDetector:
    """Get singleton detector instance."""
    global _detector
    if _detector is None:
        _detector = PlagiarismDetector()
    return _detector
