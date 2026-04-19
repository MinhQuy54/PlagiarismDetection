"""Tests for plagiarism detector."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.core.detector import (
    PlagiarismDetector,
    PlagiarismResult,
    ChunkAnalysisResult,
    PlagiarismMatch,
)
from src.core.chunker import TextChunk
from src.storage.elasticsearch import SearchResult


class TestPlagiarismDetector:
    """Test cases for PlagiarismDetector."""

    @pytest.fixture
    def mock_detector(self):
        """Create detector with mocked dependencies."""
        with patch("src.core.detector.get_es_client") as mock_es, \
             patch("src.core.detector.get_ollama_client") as mock_ollama, \
             patch("src.core.detector.get_chunker") as mock_chunker, \
             patch("src.core.detector.get_analyzer") as mock_analyzer:

            # Setup mocks
            mock_es_instance = MagicMock()
            mock_es.return_value = mock_es_instance
            mock_es_instance.get_document_count.return_value = 100

            mock_ollama_instance = MagicMock()
            mock_ollama.return_value = mock_ollama_instance

            mock_chunker_instance = MagicMock()
            mock_chunker.return_value = mock_chunker_instance

            mock_analyzer_instance = MagicMock()
            mock_analyzer.return_value = mock_analyzer_instance

            detector = PlagiarismDetector()
            detector.es_client = mock_es_instance
            detector.ollama_client = mock_ollama_instance
            detector.chunker = mock_chunker_instance
            detector.analyzer = mock_analyzer_instance

            yield detector

    def test_empty_text_returns_safe(self, mock_detector):
        """Test empty text returns SAFE result."""
        mock_detector.chunker.chunk_text.return_value = []

        result = mock_detector.check_plagiarism("")

        assert result.plagiarism_percentage == 0.0
        assert result.severity == "SAFE"
        assert len(result.matches) == 0

    def test_no_matches_returns_safe(self, mock_detector):
        """Test text with no matches returns SAFE."""
        # Setup chunks
        mock_detector.chunker.chunk_text.return_value = [
            TextChunk(
                text="Test text",
                position=0,
                start_char=0,
                end_char=9,
                word_count=2,
            )
        ]

        # Setup embeddings
        mock_detector.ollama_client.embed_batch.return_value = [[0.1] * 768]

        # No search results
        mock_detector.es_client.vector_search.return_value = []

        result = mock_detector.check_plagiarism("Test text")

        assert result.plagiarism_percentage == 0.0
        assert result.severity == "SAFE"
        assert len(result.matches) == 0

    def test_high_similarity_returns_critical(self, mock_detector):
        """Test high similarity text returns CRITICAL."""
        # Setup chunks
        mock_detector.chunker.chunk_text.return_value = [
            TextChunk(
                text="Copied text exactly",
                position=0,
                start_char=0,
                end_char=19,
                word_count=3,
            )
        ]

        # Setup embeddings
        mock_detector.ollama_client.embed_batch.return_value = [[0.1] * 768]

        # High similarity match
        mock_detector.es_client.vector_search.return_value = [
            SearchResult(
                document_id="doc1",
                chunk_id="chunk1",
                document_title="Source Document",
                matched_text="Copied text exactly",
                similarity_score=0.98,
                position=0,
            )
        ]

        # Disable AI analysis for simple test
        result = mock_detector.check_plagiarism(
            "Copied text exactly",
            include_ai_analysis=False,
        )

        assert result.plagiarism_percentage >= 95
        assert result.severity == "CRITICAL"
        assert len(result.matches) == 1

    def test_calculate_base_percentage(self, mock_detector):
        """Test base percentage calculation."""
        chunks = [
            TextChunk(text="a", position=0, start_char=0, end_char=1, word_count=10),
            TextChunk(text="b", position=1, start_char=1, end_char=2, word_count=10),
        ]

        chunk_results = [
            ChunkAnalysisResult(
                chunk_index=0,
                text="a",
                max_similarity=0.9,
                status="HIGH",
            ),
            ChunkAnalysisResult(
                chunk_index=1,
                text="b",
                max_similarity=0.5,
                status="LOW",
            ),
        ]

        percentage = mock_detector._calculate_base_percentage(chunks, chunk_results)

        # Expected: (0.9 * 10 + 0.5 * 10) / 20 * 100 = 70%
        assert percentage == 70.0

    def test_deduplicate_matches(self, mock_detector):
        """Test match deduplication by matched_chunk_id."""
        matches = [
            PlagiarismMatch(
                document_id="doc1",
                document_title="Doc 1",
                matched_text="text",
                input_text="text",
                similarity_score=0.8,
                position_start=0,
                position_end=4,
                chunk_index=0,
                matched_chunk_id="chunk_a",
            ),
            PlagiarismMatch(
                document_id="doc1",
                document_title="Doc 1",
                matched_text="text",
                input_text="text",
                similarity_score=0.7,  # Duplicate matched_chunk_id, lower score
                position_start=0,
                position_end=4,
                chunk_index=0,
                matched_chunk_id="chunk_a",
            ),
            PlagiarismMatch(
                document_id="doc1",
                document_title="Doc 1",
                matched_text="other chunk",
                input_text="other",
                similarity_score=0.9,
                position_start=5,
                position_end=10,
                chunk_index=0,  # Same input chunk, different matched chunk
                matched_chunk_id="chunk_b",
            ),
        ]

        unique = mock_detector._deduplicate_matches(matches)

        # Should keep highest score for each matched_chunk_id
        assert len(unique) == 2
        assert unique[0].similarity_score == 0.9  # Sorted by score
        assert unique[0].matched_chunk_id == "chunk_b"
        assert unique[1].similarity_score == 0.8
        assert unique[1].matched_chunk_id == "chunk_a"


class TestPlagiarismResult:
    """Test cases for PlagiarismResult dataclass."""

    def test_result_creation(self):
        """Test PlagiarismResult creation."""
        result = PlagiarismResult(
            request_id="test-123",
            plagiarism_percentage=75.5,
            severity="HIGH",
            explanation="Test explanation",
            matches=[],
            chunk_analysis=[],
            processing_time_ms=100,
            chunks_analyzed=5,
            documents_searched=1000,
        )

        assert result.request_id == "test-123"
        assert result.plagiarism_percentage == 75.5
        assert result.severity == "HIGH"
        assert result.processing_time_ms == 100
