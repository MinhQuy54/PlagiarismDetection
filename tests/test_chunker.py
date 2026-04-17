"""Tests for text chunker."""

import pytest
from src.core.chunker import TextChunker, TextChunk


class TestTextChunker:
    """Test cases for TextChunker."""

    def setup_method(self):
        """Setup test fixtures."""
        self.chunker = TextChunker(
            chunk_size=10,  # Small for testing
            chunk_overlap=2,
            min_chunk_size=3,
        )

    def test_normalize_text(self):
        """Test text normalization."""
        # Multiple spaces
        text = "Hello    world   test"
        assert self.chunker.normalize_text(text) == "Hello world test"

        # Newlines and tabs
        text = "Hello\n\nworld\ttest"
        assert self.chunker.normalize_text(text) == "Hello world test"

        # Leading/trailing whitespace
        text = "  Hello world  "
        assert self.chunker.normalize_text(text) == "Hello world"

        # Empty string
        assert self.chunker.normalize_text("") == ""
        assert self.chunker.normalize_text("   ") == ""

    def test_chunk_short_text(self):
        """Test chunking text shorter than chunk size."""
        text = "Hello world test"
        chunks = self.chunker.chunk_text(text)

        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].position == 0
        assert chunks[0].word_count == 3

    def test_chunk_long_text(self):
        """Test chunking text longer than chunk size."""
        # Create text with 25 words
        words = [f"word{i}" for i in range(25)]
        text = " ".join(words)

        chunks = self.chunker.chunk_text(text)

        # Should have multiple chunks
        assert len(chunks) > 1

        # First chunk should have chunk_size words
        assert chunks[0].word_count == 10

        # Check overlap - second chunk should start at position (chunk_size - overlap)
        assert chunks[1].position == 1

    def test_chunk_positions(self):
        """Test chunk positions are sequential."""
        words = [f"word{i}" for i in range(30)]
        text = " ".join(words)

        chunks = self.chunker.chunk_text(text)

        for i, chunk in enumerate(chunks):
            assert chunk.position == i

    def test_detect_language_english(self):
        """Test language detection for English."""
        text = "This is a test sentence in English language for detection."
        lang = self.chunker.detect_language(text)
        assert lang == "en"

    def test_detect_language_vietnamese(self):
        """Test language detection for Vietnamese."""
        text = "Đây là một câu tiếng Việt để kiểm tra phát hiện ngôn ngữ."
        lang = self.chunker.detect_language(text)
        assert lang == "vi"

    def test_detect_language_short_text(self):
        """Test language detection for short text."""
        text = "Hi"
        lang = self.chunker.detect_language(text)
        assert lang == "unknown"

    def test_split_into_sentences(self):
        """Test sentence splitting."""
        text = "Hello world. This is a test! How are you?"
        sentences = self.chunker.split_into_sentences(text)

        assert len(sentences) == 3
        assert sentences[0] == "Hello world."
        assert sentences[1] == "This is a test!"
        assert sentences[2] == "How are you?"

    def test_get_word_count(self):
        """Test word counting."""
        assert self.chunker.get_word_count("Hello world") == 2
        assert self.chunker.get_word_count("") == 0
        assert self.chunker.get_word_count("One") == 1

    def test_chunk_empty_text(self):
        """Test chunking empty text."""
        chunks = self.chunker.chunk_text("")
        assert len(chunks) == 0

        chunks = self.chunker.chunk_text("   ")
        assert len(chunks) == 0


class TestTextChunk:
    """Test cases for TextChunk dataclass."""

    def test_text_chunk_creation(self):
        """Test TextChunk creation."""
        chunk = TextChunk(
            text="Hello world",
            position=0,
            start_char=0,
            end_char=11,
            word_count=2,
        )

        assert chunk.text == "Hello world"
        assert chunk.position == 0
        assert chunk.start_char == 0
        assert chunk.end_char == 11
        assert chunk.word_count == 2
