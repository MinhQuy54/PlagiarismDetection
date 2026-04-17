
from typing import Dict, Any
import os, logging, time 
from typing import Optional 
from dataclasses import dataclass, field
from uuid import uuid4
from src.config.settings import get_settings
from src.storage.elasticsearch import es_manager
from src.embedding.ollama_embed import get_ollama_client
from src.core.analyzer import get_analyzer

logger = logging.getLogger(__name__)

class PlagiarismDetector:
    def __init__(self, threshold: float = 0.7, top_k: int = 5):
        self.es = es_manager
        self.embedder = get_ollama_client()
        self.threshold = threshold 
        self.top_k = top_k
    
    def check_plagiarism(self, text : str) -> Dict[str , Any]:
        from src.core.chunker import get_chunker
        chunker = get_chunker()
        input_chunks = chunker.chunk_text(text)
        
        results = []
        total_plagiarism_score = 0
        
        for chunk in input_chunks:
            # Lấy vector cho chunk hiện tại
            vector = self.embedder.embed(chunk.text)
            
            # Tìm kiếm các đoạn tương đồng nhất trong ES
            matches = self.es.vector_search(vector, top_k=self.top_k)
            
            # Lọc các kết quả trên ngưỡng threshold
            high_similarity_matches = [m for m in matches if m['score'] >= self.threshold]
            
            if high_similarity_matches:
                results.append({
                    "input_chunk": chunk.text,
                    "position": chunk.position,
                    "matches": high_similarity_matches
                })
                # Lấy score cao nhất của chunk này cộng dồn vào tổng
                total_plagiarism_score += max([m['score'] for m in high_similarity_matches])

        # 3. Tính toán tỷ lệ phần trăm đạo văn dự kiến
        plagiarism_percentage = (len(results) / len(input_chunks)) * 100 if input_chunks else 0
        
        return {
            "is_plagiarism": plagiarism_percentage > 20, # Ví dụ > 20% là cảnh báo
            "plagiarism_percentage": round(plagiarism_percentage, 2),
            "detailed_results": results,
            "summary": f"Tìm thấy {len(results)}/{len(input_chunks)} đoạn có dấu hiệu trùng lặp."
        }

_detector = None

def get_detector() -> PlagiarismDetector:
    global _detector
    if _detector is None:
        _detector = PlagiarismDetector()
    return _detector
