import logging
import gc, logging, os, time
from typing import Optional
from dataclasses import dataclass, field
from pathlib import Path

from unstructured.partition.pdf import partition_pdf
from unstructured.documents.elements import (
    Title,
    NarrativeText,
    ListItem,
    Table,
    Header,
    Footer,
    Text, Element,
)
from src.config.settings import get_settings
from src.core.chunker import TextChunker

logger = logging.getLogger(__name__)


@dataclass
class PdfSection:
    
    section_title : str
    content : str 
    element_type: str
    position: int
    word_count : int 


@dataclass
class PdfChunk:
    chunk_id: str
    section_title: str
    text: str
    element_type: str
    position: int
    word_count: int    
    
@dataclass
class PdfProcessingResult:
    success: bool
    document_title: str
    chunks: list[PdfChunk] = field(default_factory=list)
    total_pages: int = 0
    total_elements: int = 0
    processing_time_ms: int = 0
    pdf_metadata: dict = field(default_factory=dict)
    error_message: str = ""
    

class PdfProcessor:
    # Element types that indicate section headers/titles
    TITLE_TYPES = (Title, Header) 
    
     # Element types to include in content
    CONTENT_TYPES = (NarrativeText, ListItem, Table, Text)

    # Element types to skip
    _SKIP_TYPES = (Footer,)
    
    def __init__(
        self, 
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        min_chunk_size: Optional[int] = None,
    ):
        self.settings = get_settings()
        self.chunk_size = chunk_size or self.settings.chunk_size
        self.chunk_overlap = chunk_overlap or self.settings.chunk_overlap
        self.min_chunk_size = min_chunk_size or self.settings.min_chunk_size
        self.chunker = TextChunker(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            min_chunk_size=self.min_chunk_size, )
        
    def cut_page(self, elements: list[Element]) -> list[Element]:
        element_entry = []
        point_cut = False
        
        words_cut = ["MỤC LỤC", "TABLE OF CONTENTS", "DANH MỤC"]
        
        # Kiểm tra xem có mục lục không
        has_toc = False
        for e in elements:
            if e.text and any(word in e.text.upper() for word in words_cut):
                has_toc = True
                break
        
        if not has_toc:
            return elements

        for e in elements:
            if not e.text: continue
            text = e.text.strip().upper()
            
            if not point_cut:
                if any(word in text for word in words_cut):
                    point_cut = True 
                    continue
            else: 
                element_entry.append(e)
        
        return element_entry if element_entry else elements
    
    def process_pdf(
        self,
        pdf_path: str,
        document_id: str,
        language: Optional[str] = None,
        extract_images: bool = False,
    ) -> PdfProcessingResult:
        
        start_time = time.time()
        
        if not os.path.exists(pdf_path):
            return PdfProcessingResult(
                success=False,
                document_title="",
                error_message=f"PDF file not found: {pdf_path}",
            )
        try:
            # Extract elements from PDF using unstructured
            logger.info(f"Processing PDF: {pdf_path}")
            
            print(f"[1/5] Loading PDF: {Path(pdf_path).name}...", flush=True)
            
            # Determine languages for OCR
            languages = ["eng"]
            if language:
                if language == "vi" or language == "vie":
                    languages = ["vie", "eng"]
                else:
                    languages = [language, "eng"]
            
            elements_tmp = partition_pdf(
                filename=pdf_path,
                strategy="hi_res",  # hi_res: with OCR + deep learning
                languages=languages,
                include_page_breaks=True,
                infer_table_structure=True,
                extract_images_in_pdf=extract_images,
            )
            
            logger.info(f"Unstructured extracted {len(elements_tmp)} raw elements")
            elements = self.cut_page(elements_tmp)
            logger.info(f"After cut_page, {len(elements)} elements remain")

            print(f"[2/5] PDF loaded - extracted {len(elements)} elements", flush=True)
            
            if not elements:
                return PdfProcessingResult(
                    success=False,
                    document_title="",
                    error_message="No content extracted from PDF",
                )
            
            # Extract document title
            print("[3/5] Extracting document title...", flush=True)
            document_title = self._extract_document_title(elements, pdf_path)
            
            # Group elements by sections
            print("[4/5] Grouping elements into sections...", flush=True)
            sections = self._group_into_sections(elements)
            print(f"       Created {len(sections)} sections", flush=True)
            
            # Chunk sections into smaller chunks
            print("[5/5] Converting sections to chunks...", flush=True)
            chunks = self._sections_to_chunks(sections, document_id)
            
            processing_time = int((time.time() - start_time) * 1000)
            print(f"[DONE] Processed {len(chunks)} chunks in {processing_time}ms", flush=True)

            logger.info(
                f"Processed PDF: {len(elements)} elements -> {len(chunks)} chunks "
                f"in {processing_time}ms"
            )
            
            return PdfProcessingResult(
                success=True,
                document_title=document_title,
                chunks=chunks,
                total_pages=self._count_pages(elements),
                total_elements=len(elements),
                processing_time_ms=processing_time,
                pdf_metadata=self._extract_metadata(elements),
            )
        except Exception as e:
            logger.error(f"Error processing PDF {pdf_path}: {e}")
            return PdfProcessingResult(
                success=False,
                document_title="",
                error_message=str(e),
            )
    
    def _extract_document_title(self, elements: list, pdf_path: str) -> str:
        # Try to find first Title element
        for e in elements:
            if isinstance(e, Title):
                title = e.text.strip()
                if title:
                    return title
        
        # Fallback to filename
        return Path(pdf_path).stem
    
    def _is_likely_toc_entry_by_dots(self, text: str, dot_threshold: int = 10) -> bool:
        """Kiểm tra xem một dòng có chứa hơn X dấu chấm liên tục không."""
        # Kiểm tra chuỗi 10 dấu chấm liên tục hoặc 10 cặp '. '
        # (Đây là logic mạnh mẽ nhất để nhận diện TOC)
        return (' . ' * dot_threshold in text) or ('.' * dot_threshold in text.replace(' ', ''))
    
    def _group_into_sections(self, elements: list[Element]) -> list[PdfSection]:
        
        sections: list[PdfSection] = []
        current_title = None  # Default section name
        current_content: list[str] = []
        current_types: list[str] = []
        position = 0
        
        EXCLUDED_TITLES = [
            "MỤC LỤC", "DANH SÁCH", "DANH MỤC", "BẢNG", "HÌNH",
            "TABLE OF CONTENTS", "LIST OF FIGURES", "LIST OF TABLES",
            "ABBREVIATIONS", "TÓM TẮT", "ABSTRACT", "LỜI NÓI ĐẦU",
            "KÝ HIỆU", "TỪ VIẾT TẮT", "INTRODUCTION", "GIỚI THIỆU", "TÀI LIỆU THAM KHẢO"
        ]
        
        for e in elements:
            el_type = type(e).__name__
            
            # Skip footer elements
            if isinstance(e, self._SKIP_TYPES): continue
            
            if self._is_likely_toc_entry_by_dots(text=e.text): continue
            
            # Check if it's a title element
            is_title = False
            if isinstance(e, self.TITLE_TYPES):
                is_title = True
                new_title = str(e).strip()
                is_excluded = any(keyword in new_title.upper() for keyword in EXCLUDED_TITLES)
                if is_excluded: continue
                
                # Nếu current_title là None, nội dung hiện tại (Introduction) sẽ bị bỏ qua
                # và current_content sẽ được reset ở bước tiếp theo.
                if current_content:
                    section = self._create_section(
                        title=current_title,
                        content_parts=current_content,
                        element_types=current_types,
                        position=position,
                    )
                    if section:
                        sections.append(section)
                        position += 1
                            
                # Start new section
                current_title = new_title or "Untitled Section"
                current_content = [current_title] # Include title in content
                current_types = [el_type]
                
                
            # Add content (dành cho CONTENT_TYPES và các elements bị loại trừ)
            elif isinstance(e, self.CONTENT_TYPES):
                text = str(e).strip()
                if text:
                    current_content.append(text)
                    current_types.append(el_type)
        # Don't forget the last section
        # ... (Giữ nguyên phần này)
        if current_content:
            section = self._create_section(
                title=current_title,
                content_parts=current_content,
                element_types=current_types,
                position=position,
            )
            if section:
                sections.append(section)

        return sections
    
    def _create_section(
        self, 
        title: str,
        content_parts: list[str],
        element_types: list[str],
        position: int,
    ) -> Optional[PdfSection]:
        """Tạo một PdfSection từ các thành phần đã cho."""
        content = "\n".join(content_parts)
        content = self.chunker.normalize_text(content)
        if not content:
            return None
        word_count = len(content.split())
        
        # Determine primary element type
        element_type = "Mixed"
        if element_types:
            type_count = {}
            for i in element_types:
                type_count[i] = type_count.get(i, 0) + 1
            element_type = max(type_count, key=type_count.get)
        
        return PdfSection(
            section_title=title,
            content=content,
            element_type=element_type,
            position=position,
            word_count=word_count,
        )
    
    def _sections_to_chunks(
        self, 
        sections: list[PdfSection],
        document_id: str,
    ) -> list[PdfChunk]:
        """Chuyển đổi danh sách PdfSection thành danh sách Chunk."""
        chunks: list[PdfChunk] = []
        chunk_position = 0
        skipped_count = 0
        
        for section in sections:
            # Skip sections with content shorter than 10 characters
                # logger.info(f"Section '{section.section_title}' content length: {len(section.content)}")
            if len(section.content) < self.settings.min_content_length:
                skipped_count += 1
                logger.info(
                    f"Skipping short section '{section.section_title}': "
                    f"{len(section.content)} chars < {self.settings.min_content_length}"
                )
                continue
            
            # Check if section needs to be split
            if section.word_count <= self.chunk_size:
                chunk = PdfChunk(
                    chunk_id=f"{document_id}_chunk_{chunk_position}",
                    section_title=section.section_title,
                    text=section.content,
                    element_type=section.element_type,
                    position=chunk_position,
                    word_count=section.word_count,
                )
                chunks.append(chunk)
                chunk_position += 1
                
            else:
                # Split section into multiple chunks
                text_chunks = self.chunker.chunk_text(section.content)

                for i, text_chunk in enumerate(text_chunks):
                    # Skip sub-chunks that are too short
                    if len(text_chunk.text) < self.settings.min_content_length:
                        skipped_count += 1
                        continue

                    # Add section context to title for sub-chunks
                    if len(text_chunks) > 1:
                        chunk_title = f"{section.section_title} (part {i + 1}/{len(text_chunks)})"
                    else:
                        chunk_title = section.section_title

                    chunk = PdfChunk(
                        chunk_id=f"{document_id}_chunk_{chunk_position}",
                        section_title=chunk_title,
                        text=text_chunk.text,
                        element_type=section.element_type,
                        position=chunk_position,
                        word_count=text_chunk.word_count,
                    )
                    chunks.append(chunk)
                    chunk_position += 1

        if skipped_count > 0:
            logger.info(f"Skipped {skipped_count} chunks with content < {self.settings.min_content_length} chars")

        return chunks
    
    def _count_pages(self, elements: list) -> int:
        """Count pages from page break elements."""
        from unstructured.documents.elements import PageBreak

        page_count = 1
        for el in elements:
            if isinstance(el, PageBreak):
                page_count += 1
        return page_count

    def _extract_metadata(self, elements: list) -> dict:
        """Extract any available metadata from elements."""
        metadata = {}

        # Try to get metadata from first element if available
        if elements and hasattr(elements[0], "metadata"):
            el_meta = elements[0].metadata
            if hasattr(el_meta, "filename"):
                metadata["filename"] = el_meta.filename
            if hasattr(el_meta, "filetype"):
                metadata["filetype"] = el_meta.filetype
            if hasattr(el_meta, "page_number"):
                metadata["first_page"] = el_meta.page_number

        return metadata


# Singleton instance
_pdf_processor: Optional[PdfProcessor] = None


def get_pdf_processor() -> PdfProcessor:
    """Get singleton PDF processor instance."""
    global _pdf_processor
    if _pdf_processor is None:
        _pdf_processor = PdfProcessor()
    return _pdf_processor
