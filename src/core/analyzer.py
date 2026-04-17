import logging, json, httpx
from typing import Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    plagiarism_percentage: float
    severity: str
    explanation: str
    suspicious_segments: list[dict]
    confidence: float


class BaseAnalyzer(ABC):
    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[httpx.Client] = None
         
    @abstractmethod
    def analyze( self, input_text: str, matches: list[dict], base_percentage: float) -> AnalysisResult:
        pass
    
    def _format_matches(self, matches: list[dict]) -> str:
        
        formatted = []
        if not matches:
            return "No matches found"
        
        for i, match in enumerate(matches[:5], 1):
            formatted.append(
                f""" 
                Match {i}: 
                - Source: {match.get('source', 'Unknown')}
                - Similarity: {match.get('similarity', 0):.2%}
                - Matched Text: {match.get('matched_text', '')[:200]}...
                """
            )
        return "\n".join(formatted)
    
    def _prompt(
        self, input_text: str, matches_text: str, base_percentage: float
    ) -> str:
        truncated_input = input_text[:2000] + "..." if len(input_text) > 2000 else input_text

        return f"""Bạn là chuyên gia kiểm tra đạo văn. Bạn hãy phân tích văn bản sau và đưa ra đánh giá.
        VĂN BẢN CẦN KIỂM TRA:
        \"\"\"{truncated_input}\"\"\"

        CÁC KẾT QUẢ TƯƠNG TỰ TÌM THẤY:
        {matches_text}

        ĐIỂM TƯƠNG ĐỒNG CƠ BẢN: {base_percentage:.1f}%

        Hãy phân tích và trả lời theo format JSON sau:
        {{
            "plagiarism_percentage": <số từ 0-100>,
            "severity": "<SAFE|LOW|MEDIUM|HIGH|CRITICAL>",
            "explanation": "<giải thích ngắn gọn bằng tiếng Việt>",
            "suspicious_segments": [
                {{
                    "text": "<đoạn văn bị nghi ngờ>",
                    "reason": "<lý do nghi ngờ>"
                }}
            ],
            "confidence": <độ tin cậy từ 0-1>
        }}

        Lưu ý:
        - CRITICAL (>=95%): Copy nguyên văn, đạo văn nghiêm trọng
        - HIGH (85-94%): Đạo văn cao, paraphrase nhẹ
        - MEDIUM (70-84%): Nghi ngờ đạo văn, paraphrase nhiều
        - LOW (50-69%): Có thể trùng ý tưởng
        - SAFE (<50%): An toàn, không đạo văn

        Chỉ trả về JSON, không có text khác."""
    
    def _parse_response(self, response_text: str, base_percentage : float) -> AnalysisResult:
        try:
            response_text = response_text.strip()
            data = json.loads(response_text)
            
            return AnalysisResult(
                plagiarism_percentage=float(data.get("plagiarism_percentage", base_percentage)),
                severity=data.get("severity", self._get_severity(base_percentage)),
                explanation=data.get("explanation", "No Analysis Detail"),
                suspicious_segments=data.get("suspicious_segments", []),
                confidence=float(data.get("confidence", 0.0)),
            )
        except Exception as e:
            logger.error(f"Error parsing analysis response: {e}")
            return AnalysisResult(
                plagiarism_percentage=base_percentage,
                severity=self._get_severity(base_percentage),
                explanation="Error parsing analysis response",
                suspicious_segments=[],
                confidence=0.0,
            )
    
    def _fallack_severity(self, percentage: float) -> AnalysisResult:
        return AnalysisResult(
            plagiarism_percentage=percentage,
            severity=self._get_severity(percentage),
            explanation="Phân tích dựa trên độ tương đồng vector. AI analysis không khả dụng.",
            suspicious_segments=[],
            confidence=0.6,
        )
    
    def _get_severity(self, percentage: float) -> str:
        if percentage >= 95: return "CRITICAL"
        if percentage >= 85: return "HIGH"
        if percentage >= 70: return "MEDIUM"
        if percentage >= 50: return "LOW"
        return "SAFE"

    def close(self):
        if self._client:
            self._client.close()
            self._client = None


class OllamaAnalyzer(BaseAnalyzer):
    def __init__(self):
        super().__init__()
        self.base_url = self.settings.ollama_host
        self.model = self.settings.ollama_chat_model
        self.timeout = self.settings.ollama_timeout
    
    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            logger.info(f"Initializing Ollama client for {self.base_url}")
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout)
            )
        return self._client
    
    def analyze(
        self,
        input_text: str,
        matches: list[dict],
        base_percentage: float
    ) -> AnalysisResult:
        matches_text = self._format_matches(matches)
        prompt = self._prompt(input_text, matches_text, base_percentage)

        try:
            response = self.client.post(
                "/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.2,
                        "top_p": 0.9,
                        "top_k": 40,
                        "num_predict": 500, # Giới hạn độ dài
                        "repeat_penalty": 1.1,
                        "presence_penalty": 0.0,
                        "frequency_penalty": 0.0,
                        "stop": ["\n\n"],
                    }
                },
            )
            response.raise_for_status()
            data = response.json()
            return self._parse_response(data.get("response", ""), base_percentage)
        except Exception as e:
            logger.error(f"Ollama analysis failed: {e}")
            return self._fallack_severity(base_percentage)
    
    
_analyzer: Optional[BaseAnalyzer] = None

def get_analyze() -> BaseAnalyzer:
    
    global _analyzer
    if _analyzer is None:
        _analyzer = OllamaAnalyzer()
    return _analyzer