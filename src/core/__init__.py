# Core business logic
from .chunker import TextChunker, TextChunk, get_chunker
from .analyzer import OllamaAnalyzer, AnalysisResult, get_analyzer
from .detector import (
    PlagiarismDetector,
    PlagiarismResult,
    PdfPlagiarismResult,
    PdfCheckMetadata,
    PdfTextChunk,
    get_detector,
)
from .document_manager import DocumentManager, UploadResult, PdfUploadResult, get_document_manager
from .processor import PdfProcessor, PdfChunk, PdfProcessingResult, get_pdf_processor

__all__ = [
    "TextChunker",
    "TextChunk",
    "get_chunker",
    "OllamaAnalyzer",
    "AnalysisResult",
    "get_analyzer",
    "PlagiarismDetector",
    "PlagiarismResult",
    "PdfPlagiarismResult",
    "PdfCheckMetadata",
    "PdfTextChunk",
    "get_detector",
    "DocumentManager",
    "UploadResult",
    "PdfUploadResult",
    "get_document_manager",
    "PdfProcessor",
    "PdfChunk",
    "PdfProcessingResult",
    "get_pdf_processor",
]
