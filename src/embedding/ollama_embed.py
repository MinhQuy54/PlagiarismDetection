
import httpx, logging
from typing import Optional
from src.config.settings import get_settings

logger = logging.getLogger(__name__)

class OllamaEmbeddingClient:
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.ollama_host
        self.model = self.settings.ollama_embed_model
        self.timeout = self.settings.ollama_timeout
        self._client: Optional[httpx.Client] = None
        
        
    # Singleton/Lazy Loading
    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout)
            )
        return self._client
    
    def health_check(self) -> dict:
        try:
            response = self.client.get("/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_name = [m["name"] for m in models]
                has_embed_model = any(
                    self.model in name for name in model_name)
                
                return {
                    "healthy" : True,
                    "models": model_name,
                    "embed_model_available": has_embed_model,
                }
            return {"healthy": False, "error": f"Status: {response.status_code}"}
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return {"healthy": False, "error": str(e)}
        
    # Convert Text to Vector
    def embed(self, text: str) -> list[float]:
        try:
            response = self.client.post(
                "/api/embed",
                json={
                    "model": self.model,
                    "input": text
                }
            )
            response.raise_for_status()
            data = response.json()
            if "embeddings" in data and len(data["embeddings"]) > 0:
                return data["embeddings"][0]
            return data.get("embedding", [])
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            raise
    
    # 32
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        batch_size = self.settings.embedding_batch_size
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            try:
                response = self.client.post(
                    "/api/embed",
                    json={
                        "model": self.model,
                        "input": batch,
                    },
                )
                response.raise_for_status()
                data = response.json()

                if "embeddings" in data:
                    all_embeddings.extend(data["embeddings"])
                elif "embedding" in data:
                    all_embeddings.append(data["embedding"])
                else:
                    raise ValueError(f"Unexpected response format: {data.keys()}")

            except httpx.HTTPStatusError as e:
                logger.error(f"Batch embedding failed: {e.response.text}")
                for text in batch:
                    all_embeddings.append(self.embed(text))

        return all_embeddings
        
    def close(self):
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None


_ollama_client: Optional[OllamaEmbeddingClient] = None


def get_ollama_client() -> OllamaEmbeddingClient:
    """Get singleton Ollama client instance."""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaEmbeddingClient()
    return _ollama_client

            