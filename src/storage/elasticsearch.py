import logging
from datetime import datetime
from typing import List, Optional

from elasticsearch import Elasticsearch, helpers
from src.config.settings import  get_settings

logger = logging.getLogger(__name__)

class ESClient:
    def __init__(self):
        es_url = f"{get_settings().es_scheme}://{get_settings().es_host}:{get_settings().es_port}"
        
        logger.info(f"Connecting to Elasticsearch at: {es_url}")
        
        self.client = Elasticsearch(
            es_url, 
            retry_on_timeout=True,
            max_retries=3
        )
            
    def create_index(self):
        index_name = get_settings().es_index
        mapping = {
            "mappings": {
                "properties": {
                    "document_id": {"type": "keyword"},
                    "chunk_id": {"type": "keyword"},
                    "content": {"type": "text"},
                    "vector": {
                        "type": "dense_vector",
                        "dims": 768, # kich thuoc vector
                        "index": True,
                        "similarity": "cosine" # thuat toan do khoang cach 
                    },
                    "metadata": {"type": "object"},
                    "created_at": {"type": "date"}
                }
            }
        }
        try:
            if not self.client.indices.exists(index=index_name):
                self.client.indices.create(index=index_name, body=mapping)
                logger.info(f"✅ Index '{index_name}' created successfully")
            else: 
                logger.info(f"Index '{index_name}' already exists")
        except Exception as e: 
            logger.error(f"Error creating index: {e}")

    def bulk_index_chunks(self, chunks: List[dict]):
        """Nạp nhiều đoạn văn bản cùng lúc vào ES"""
        actions = [
            {
                "_index": get_settings().es_index,
                "_source": {
                    **chunk,
                    "created_at": datetime.utcnow()
                }
            }
            for chunk in chunks
        ]
        try:
            success, _ = helpers.bulk(self.client, actions)
            return success
        except Exception as e:
            logger.error(f"Bulk indexing error: {e}")
            return 0
        
    def vector_search(self, query_vector: List[float], top_k: int = 5):
        """Tìm kiếm các đoạn văn tương đồng bằng kNN"""
        knn_query = {
            "field": "vector",
            "query_vector": query_vector,
            "k": top_k,
            "num_candidates": 100
        }
        try:
            response = self.client.search(
                index=get_settings().es_index,
                knn=knn_query,
                source=["document_id", "content", "metadata"]
            )
            return response['hits']['hits']
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []

    def delete_by_document_id(self, document_id: str):
        """Xóa toàn bộ các chunk của một tài liệu"""
        query = {"query": {"term": {"document_id": document_id}}}
        try:
            return self.client.delete_by_query(index=get_settings().es_index, body=query)
        except Exception as e:
            logger.error(f"Delete error: {e}")
            return None

    def check_health(self):
        return self.client.ping()

es_manager = ESClient()