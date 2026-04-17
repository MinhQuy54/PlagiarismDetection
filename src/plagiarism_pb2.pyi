from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Severity(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SAFE: _ClassVar[Severity]
    LOW: _ClassVar[Severity]
    MEDIUM: _ClassVar[Severity]
    HIGH: _ClassVar[Severity]
    CRITICAL: _ClassVar[Severity]
SAFE: Severity
LOW: Severity
MEDIUM: Severity
HIGH: Severity
CRITICAL: Severity

class CheckRequest(_message.Message):
    __slots__ = ("text", "options")
    TEXT_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    text: str
    options: CheckOptions
    def __init__(self, text: _Optional[str] = ..., options: _Optional[_Union[CheckOptions, _Mapping]] = ...) -> None: ...

class CheckOptions(_message.Message):
    __slots__ = ("min_similarity", "top_k", "include_ai_analysis", "exclude_docs")
    MIN_SIMILARITY_FIELD_NUMBER: _ClassVar[int]
    TOP_K_FIELD_NUMBER: _ClassVar[int]
    INCLUDE_AI_ANALYSIS_FIELD_NUMBER: _ClassVar[int]
    EXCLUDE_DOCS_FIELD_NUMBER: _ClassVar[int]
    min_similarity: float
    top_k: int
    include_ai_analysis: bool
    exclude_docs: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, min_similarity: _Optional[float] = ..., top_k: _Optional[int] = ..., include_ai_analysis: bool = ..., exclude_docs: _Optional[_Iterable[str]] = ...) -> None: ...

class CheckResponse(_message.Message):
    __slots__ = ("request_id", "plagiarism_percentage", "severity", "explanation", "matches", "chunks", "metadata")
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    PLAGIARISM_PERCENTAGE_FIELD_NUMBER: _ClassVar[int]
    SEVERITY_FIELD_NUMBER: _ClassVar[int]
    EXPLANATION_FIELD_NUMBER: _ClassVar[int]
    MATCHES_FIELD_NUMBER: _ClassVar[int]
    CHUNKS_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    plagiarism_percentage: float
    severity: Severity
    explanation: str
    matches: _containers.RepeatedCompositeFieldContainer[Match]
    chunks: _containers.RepeatedCompositeFieldContainer[ChunkAnalysis]
    metadata: Metadata
    def __init__(self, request_id: _Optional[str] = ..., plagiarism_percentage: _Optional[float] = ..., severity: _Optional[_Union[Severity, str]] = ..., explanation: _Optional[str] = ..., matches: _Optional[_Iterable[_Union[Match, _Mapping]]] = ..., chunks: _Optional[_Iterable[_Union[ChunkAnalysis, _Mapping]]] = ..., metadata: _Optional[_Union[Metadata, _Mapping]] = ...) -> None: ...

class Match(_message.Message):
    __slots__ = ("document_id", "document_title", "matched_text", "input_text", "similarity_score", "position")
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    DOCUMENT_TITLE_FIELD_NUMBER: _ClassVar[int]
    MATCHED_TEXT_FIELD_NUMBER: _ClassVar[int]
    INPUT_TEXT_FIELD_NUMBER: _ClassVar[int]
    SIMILARITY_SCORE_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    document_id: str
    document_title: str
    matched_text: str
    input_text: str
    similarity_score: float
    position: Position
    def __init__(self, document_id: _Optional[str] = ..., document_title: _Optional[str] = ..., matched_text: _Optional[str] = ..., input_text: _Optional[str] = ..., similarity_score: _Optional[float] = ..., position: _Optional[_Union[Position, _Mapping]] = ...) -> None: ...

class Position(_message.Message):
    __slots__ = ("start_char", "end_char", "start_word", "end_word")
    START_CHAR_FIELD_NUMBER: _ClassVar[int]
    END_CHAR_FIELD_NUMBER: _ClassVar[int]
    START_WORD_FIELD_NUMBER: _ClassVar[int]
    END_WORD_FIELD_NUMBER: _ClassVar[int]
    start_char: int
    end_char: int
    start_word: int
    end_word: int
    def __init__(self, start_char: _Optional[int] = ..., end_char: _Optional[int] = ..., start_word: _Optional[int] = ..., end_word: _Optional[int] = ...) -> None: ...

class ChunkAnalysis(_message.Message):
    __slots__ = ("chunk_index", "text", "similarity_score", "is_plagiarized", "source_document_id", "source_text")
    CHUNK_INDEX_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    SIMILARITY_SCORE_FIELD_NUMBER: _ClassVar[int]
    IS_PLAGIARIZED_FIELD_NUMBER: _ClassVar[int]
    SOURCE_DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    SOURCE_TEXT_FIELD_NUMBER: _ClassVar[int]
    chunk_index: int
    text: str
    similarity_score: float
    is_plagiarized: bool
    source_document_id: str
    source_text: str
    def __init__(self, chunk_index: _Optional[int] = ..., text: _Optional[str] = ..., similarity_score: _Optional[float] = ..., is_plagiarized: bool = ..., source_document_id: _Optional[str] = ..., source_text: _Optional[str] = ...) -> None: ...

class Metadata(_message.Message):
    __slots__ = ("processing_time_ms", "chunks_analyzed", "documents_searched", "model_used")
    PROCESSING_TIME_MS_FIELD_NUMBER: _ClassVar[int]
    CHUNKS_ANALYZED_FIELD_NUMBER: _ClassVar[int]
    DOCUMENTS_SEARCHED_FIELD_NUMBER: _ClassVar[int]
    MODEL_USED_FIELD_NUMBER: _ClassVar[int]
    processing_time_ms: int
    chunks_analyzed: int
    documents_searched: int
    model_used: str
    def __init__(self, processing_time_ms: _Optional[int] = ..., chunks_analyzed: _Optional[int] = ..., documents_searched: _Optional[int] = ..., model_used: _Optional[str] = ...) -> None: ...

class UploadRequest(_message.Message):
    __slots__ = ("title", "content", "metadata", "language")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    TITLE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    title: str
    content: str
    metadata: _containers.ScalarMap[str, str]
    language: str
    def __init__(self, title: _Optional[str] = ..., content: _Optional[str] = ..., metadata: _Optional[_Mapping[str, str]] = ..., language: _Optional[str] = ...) -> None: ...

class UploadResponse(_message.Message):
    __slots__ = ("document_id", "title", "chunks_created", "message", "success")
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    CHUNKS_CREATED_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    document_id: str
    title: str
    chunks_created: int
    message: str
    success: bool
    def __init__(self, document_id: _Optional[str] = ..., title: _Optional[str] = ..., chunks_created: _Optional[int] = ..., message: _Optional[str] = ..., success: bool = ...) -> None: ...

class BatchUploadResponse(_message.Message):
    __slots__ = ("total_documents", "successful", "failed", "results")
    TOTAL_DOCUMENTS_FIELD_NUMBER: _ClassVar[int]
    SUCCESSFUL_FIELD_NUMBER: _ClassVar[int]
    FAILED_FIELD_NUMBER: _ClassVar[int]
    RESULTS_FIELD_NUMBER: _ClassVar[int]
    total_documents: int
    successful: int
    failed: int
    results: _containers.RepeatedCompositeFieldContainer[UploadResult]
    def __init__(self, total_documents: _Optional[int] = ..., successful: _Optional[int] = ..., failed: _Optional[int] = ..., results: _Optional[_Iterable[_Union[UploadResult, _Mapping]]] = ...) -> None: ...

class UploadResult(_message.Message):
    __slots__ = ("document_id", "title", "success", "error")
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    document_id: str
    title: str
    success: bool
    error: str
    def __init__(self, document_id: _Optional[str] = ..., title: _Optional[str] = ..., success: bool = ..., error: _Optional[str] = ...) -> None: ...

class GetDocumentRequest(_message.Message):
    __slots__ = ("document_id", "include_content", "include_chunks")
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    INCLUDE_CONTENT_FIELD_NUMBER: _ClassVar[int]
    INCLUDE_CHUNKS_FIELD_NUMBER: _ClassVar[int]
    document_id: str
    include_content: bool
    include_chunks: bool
    def __init__(self, document_id: _Optional[str] = ..., include_content: bool = ..., include_chunks: bool = ...) -> None: ...

class GetDocumentResponse(_message.Message):
    __slots__ = ("document", "found")
    DOCUMENT_FIELD_NUMBER: _ClassVar[int]
    FOUND_FIELD_NUMBER: _ClassVar[int]
    document: Document
    found: bool
    def __init__(self, document: _Optional[_Union[Document, _Mapping]] = ..., found: bool = ...) -> None: ...

class Document(_message.Message):
    __slots__ = ("document_id", "title", "content", "metadata", "language", "chunk_count", "chunks", "created_at", "updated_at")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    CHUNK_COUNT_FIELD_NUMBER: _ClassVar[int]
    CHUNKS_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    UPDATED_AT_FIELD_NUMBER: _ClassVar[int]
    document_id: str
    title: str
    content: str
    metadata: _containers.ScalarMap[str, str]
    language: str
    chunk_count: int
    chunks: _containers.RepeatedCompositeFieldContainer[Chunk]
    created_at: str
    updated_at: str
    def __init__(self, document_id: _Optional[str] = ..., title: _Optional[str] = ..., content: _Optional[str] = ..., metadata: _Optional[_Mapping[str, str]] = ..., language: _Optional[str] = ..., chunk_count: _Optional[int] = ..., chunks: _Optional[_Iterable[_Union[Chunk, _Mapping]]] = ..., created_at: _Optional[str] = ..., updated_at: _Optional[str] = ...) -> None: ...

class Chunk(_message.Message):
    __slots__ = ("chunk_id", "text", "position", "word_count")
    CHUNK_ID_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    WORD_COUNT_FIELD_NUMBER: _ClassVar[int]
    chunk_id: str
    text: str
    position: int
    word_count: int
    def __init__(self, chunk_id: _Optional[str] = ..., text: _Optional[str] = ..., position: _Optional[int] = ..., word_count: _Optional[int] = ...) -> None: ...

class DeleteDocumentRequest(_message.Message):
    __slots__ = ("document_id",)
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    document_id: str
    def __init__(self, document_id: _Optional[str] = ...) -> None: ...

class DeleteDocumentResponse(_message.Message):
    __slots__ = ("success", "message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    def __init__(self, success: bool = ..., message: _Optional[str] = ...) -> None: ...

class SearchRequest(_message.Message):
    __slots__ = ("query", "filters", "limit", "offset")
    class FiltersEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    QUERY_FIELD_NUMBER: _ClassVar[int]
    FILTERS_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    OFFSET_FIELD_NUMBER: _ClassVar[int]
    query: str
    filters: _containers.ScalarMap[str, str]
    limit: int
    offset: int
    def __init__(self, query: _Optional[str] = ..., filters: _Optional[_Mapping[str, str]] = ..., limit: _Optional[int] = ..., offset: _Optional[int] = ...) -> None: ...

class SearchResponse(_message.Message):
    __slots__ = ("documents", "total")
    DOCUMENTS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_FIELD_NUMBER: _ClassVar[int]
    documents: _containers.RepeatedCompositeFieldContainer[DocumentSummary]
    total: int
    def __init__(self, documents: _Optional[_Iterable[_Union[DocumentSummary, _Mapping]]] = ..., total: _Optional[int] = ...) -> None: ...

class DocumentSummary(_message.Message):
    __slots__ = ("document_id", "title", "metadata", "language", "chunk_count", "created_at")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    CHUNK_COUNT_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    document_id: str
    title: str
    metadata: _containers.ScalarMap[str, str]
    language: str
    chunk_count: int
    created_at: str
    def __init__(self, document_id: _Optional[str] = ..., title: _Optional[str] = ..., metadata: _Optional[_Mapping[str, str]] = ..., language: _Optional[str] = ..., chunk_count: _Optional[int] = ..., created_at: _Optional[str] = ...) -> None: ...

class HealthCheckRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class HealthCheckResponse(_message.Message):
    __slots__ = ("healthy", "details")
    class DetailsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    HEALTHY_FIELD_NUMBER: _ClassVar[int]
    DETAILS_FIELD_NUMBER: _ClassVar[int]
    healthy: bool
    details: _containers.ScalarMap[str, str]
    def __init__(self, healthy: bool = ..., details: _Optional[_Mapping[str, str]] = ...) -> None: ...

class ComponentHealth(_message.Message):
    __slots__ = ("healthy", "message", "latency_ms")
    HEALTHY_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    LATENCY_MS_FIELD_NUMBER: _ClassVar[int]
    healthy: bool
    message: str
    latency_ms: int
    def __init__(self, healthy: bool = ..., message: _Optional[str] = ..., latency_ms: _Optional[int] = ...) -> None: ...

class IndexDocumentFromMinioRequest(_message.Message):
    __slots__ = ("bucket_name", "object_path", "document_id", "title", "metadata", "language")
    class MetadataEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: str
        def __init__(self, key: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...
    BUCKET_NAME_FIELD_NUMBER: _ClassVar[int]
    OBJECT_PATH_FIELD_NUMBER: _ClassVar[int]
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    METADATA_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    bucket_name: str
    object_path: str
    document_id: str
    title: str
    metadata: _containers.ScalarMap[str, str]
    language: str
    def __init__(self, bucket_name: _Optional[str] = ..., object_path: _Optional[str] = ..., document_id: _Optional[str] = ..., title: _Optional[str] = ..., metadata: _Optional[_Mapping[str, str]] = ..., language: _Optional[str] = ...) -> None: ...

class IndexDocumentFromMinioResponse(_message.Message):
    __slots__ = ("success", "document_id", "title", "chunks", "message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    DOCUMENT_ID_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    CHUNKS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    document_id: str
    title: str
    chunks: _containers.RepeatedCompositeFieldContainer[PdfChunkInfo]
    message: str
    def __init__(self, success: bool = ..., document_id: _Optional[str] = ..., title: _Optional[str] = ..., chunks: _Optional[_Iterable[_Union[PdfChunkInfo, _Mapping]]] = ..., message: _Optional[str] = ...) -> None: ...

class PdfChunkInfo(_message.Message):
    __slots__ = ("chunk_id", "section_title", "content_preview", "element_type", "position")
    CHUNK_ID_FIELD_NUMBER: _ClassVar[int]
    SECTION_TITLE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_PREVIEW_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    chunk_id: str
    section_title: str
    content_preview: str
    element_type: str
    position: int
    def __init__(self, chunk_id: _Optional[str] = ..., section_title: _Optional[str] = ..., content_preview: _Optional[str] = ..., element_type: _Optional[str] = ..., position: _Optional[int] = ...) -> None: ...

class PdfProcessingMetadata(_message.Message):
    __slots__ = ("total_pages", "total_elements", "total_chunks", "processing_time_ms", "pdf_title", "pdf_author")
    TOTAL_PAGES_FIELD_NUMBER: _ClassVar[int]
    TOTAL_ELEMENTS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_CHUNKS_FIELD_NUMBER: _ClassVar[int]
    PROCESSING_TIME_MS_FIELD_NUMBER: _ClassVar[int]
    PDF_TITLE_FIELD_NUMBER: _ClassVar[int]
    PDF_AUTHOR_FIELD_NUMBER: _ClassVar[int]
    total_pages: int
    total_elements: int
    total_chunks: int
    processing_time_ms: int
    pdf_title: str
    pdf_author: str
    def __init__(self, total_pages: _Optional[int] = ..., total_elements: _Optional[int] = ..., total_chunks: _Optional[int] = ..., processing_time_ms: _Optional[int] = ..., pdf_title: _Optional[str] = ..., pdf_author: _Optional[str] = ...) -> None: ...

class CheckDocumentFromMinioRequest(_message.Message):
    __slots__ = ("bucket_name", "object_path", "options")
    BUCKET_NAME_FIELD_NUMBER: _ClassVar[int]
    OBJECT_PATH_FIELD_NUMBER: _ClassVar[int]
    OPTIONS_FIELD_NUMBER: _ClassVar[int]
    bucket_name: str
    object_path: str
    options: CheckOptions
    def __init__(self, bucket_name: _Optional[str] = ..., object_path: _Optional[str] = ..., options: _Optional[_Union[CheckOptions, _Mapping]] = ...) -> None: ...

class CheckDocumentFromMinioResponse(_message.Message):
    __slots__ = ("success", "request_id", "plagiarism_percentage", "severity", "explanation", "matches", "error_message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    PLAGIARISM_PERCENTAGE_FIELD_NUMBER: _ClassVar[int]
    SEVERITY_FIELD_NUMBER: _ClassVar[int]
    EXPLANATION_FIELD_NUMBER: _ClassVar[int]
    MATCHES_FIELD_NUMBER: _ClassVar[int]
    ERROR_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    request_id: str
    plagiarism_percentage: float
    severity: Severity
    explanation: str
    matches: _containers.RepeatedCompositeFieldContainer[Match]
    error_message: str
    def __init__(self, success: bool = ..., request_id: _Optional[str] = ..., plagiarism_percentage: _Optional[float] = ..., severity: _Optional[_Union[Severity, str]] = ..., explanation: _Optional[str] = ..., matches: _Optional[_Iterable[_Union[Match, _Mapping]]] = ..., error_message: _Optional[str] = ...) -> None: ...

class PdfCheckMetadata(_message.Message):
    __slots__ = ("processing_time_ms", "pdf_extraction_time_ms", "embedding_time_ms", "search_time_ms", "total_pages", "total_chunks", "chunks_analyzed", "documents_searched", "model_used")
    PROCESSING_TIME_MS_FIELD_NUMBER: _ClassVar[int]
    PDF_EXTRACTION_TIME_MS_FIELD_NUMBER: _ClassVar[int]
    EMBEDDING_TIME_MS_FIELD_NUMBER: _ClassVar[int]
    SEARCH_TIME_MS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_PAGES_FIELD_NUMBER: _ClassVar[int]
    TOTAL_CHUNKS_FIELD_NUMBER: _ClassVar[int]
    CHUNKS_ANALYZED_FIELD_NUMBER: _ClassVar[int]
    DOCUMENTS_SEARCHED_FIELD_NUMBER: _ClassVar[int]
    MODEL_USED_FIELD_NUMBER: _ClassVar[int]
    processing_time_ms: int
    pdf_extraction_time_ms: int
    embedding_time_ms: int
    search_time_ms: int
    total_pages: int
    total_chunks: int
    chunks_analyzed: int
    documents_searched: int
    model_used: str
    def __init__(self, processing_time_ms: _Optional[int] = ..., pdf_extraction_time_ms: _Optional[int] = ..., embedding_time_ms: _Optional[int] = ..., search_time_ms: _Optional[int] = ..., total_pages: _Optional[int] = ..., total_chunks: _Optional[int] = ..., chunks_analyzed: _Optional[int] = ..., documents_searched: _Optional[int] = ..., model_used: _Optional[str] = ...) -> None: ...
