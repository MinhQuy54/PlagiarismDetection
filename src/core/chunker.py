import re, logging
from typing import Optional
from dataclasses import dataclass
from langdetect import LangDetectException, detect
from src.config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    text: str
    position: int
    start_char: int
    end_char: int
    word_count: int

class TextChunker:
    def __init__(
        self, 
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        min_chunk_size: Optional[int] = None
    ): 
        settings = get_settings()
        self.chunk_size = chunk_size or settings.chunk_size
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap
        self.min_chunk_size = min_chunk_size or settings.min_chunk_size
    
    # OverLap : a[] 0 - 10 --> b[] 8 - 18 
    def chunk_text(self, text: str) -> list[TextChunk]:
        # Normalize text first
        text = self.normalize_text(text)
        
        if not text: return []
        
        # Split into words
        word = text.split()
        
        if len(word) <= self.chunk_size:
            # Text is smaller than chunk size, return as single chunk
            return [TextChunk(text=text, position=0, start_char=0, end_char=len(text), word_count=len(word))]
        
        chunks = []
        position = 0
        word_index = 0
        
        while word_index < len(word):
            chunk_words = word[word_index : word_index + self.chunk_size]
            if len(chunk_words) < self.min_chunk_size:
                if chunks:
                    break

            chunk_text = " ".join(chunk_words)
            
            start_char = self._find_char_position(text, word_index, word)
            end_char = start_char + len(chunk_text)
            chunks.append(
                TextChunk(
                    text=chunk_text,
                    position=position,
                    start_char=start_char,
                    end_char=end_char,
                    word_count=len(chunk_words),
                )
            )

            position += 1
            word_index += self.chunk_size - self.chunk_overlap

        return chunks
    def normalize_text(self, text: str) -> str:
        if not text:
            return ""

        # Replace multiple whitespace with single space
        text = re.sub(r"\s+", " ", text)

        # Remove control characters
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)

        return text.strip()
    
    def _find_char_position(
        self, text: str, word_index: int, words: list[str]
    ) -> int:
        if word_index == 0:
            return 0

        # Count characters up to this word
        char_pos = 0
        for i in range(word_index):
            char_pos += len(words[i]) + 1  # +1 for space

        return min(char_pos, len(text))
    
    def detect_language(self, text : str) -> str:
        try:
            if len(text) < 20:
                return "unknown"
            lang = detect(text)
            return lang
        except LangDetectException:
            return "unknown"
    
    def split_into_sentences(self, text: str) -> list[str]:
        text = self.normalize_text(text)

        sentences = re.split(r"(?<=[.!?])\s+", text)
        sentences = [s.strip() for s in sentences if s.strip()]

        return sentences

    def chunk_by_sentence(self, text: str, max_sentences: int = 5) -> list[TextChunk]:
        sentences = self.split_by_sentence(text)
        if not sentences:
            return []
        chunks = []
        position = 0
        current_chunk_sentences = []
        
        for s in sentences:
            current_chunk_sentences.append(s)
            if len(current_chunk_sentences) >= max_sentences:
                chunk_text = " ".join(current_chunk_sentences)
                start_char = self._find_char_position(text, position, sentences)
                end_char = start_char + len(chunk_text)
                chunks.append(
                    TextChunk(
                        text=chunk_text,
                        position=position,
                        start_char=start_char,
                        end_char=end_char,
                        word_count=len(chunk_text.split()),
                    )
                )
                position += 1
                current_chunk_sentences = []
        
        if current_chunk_sentences:
            chunk_text = " ".join(current_chunk_sentences)
            start_char = self._find_char_position(text, position, sentences)
            end_char = start_char + len(chunk_text)
            chunks.append(
                TextChunk(
                    text=chunk_text,
                    position=position,
                    start_char=start_char,
                    end_char=end_char,
                    word_count=len(chunk_text.split()),
                )
            )
        
        return chunks
    
    def get_word_count(self, text: str) -> int:
        if not text:
            return 0
        return len(text.split())


# Singleton
_chunker: Optional[TextChunker] = None


def get_chunker() -> TextChunker:
    global _chunker
    if _chunker is None:
        _chunker = TextChunker()
    return _chunker

        
        