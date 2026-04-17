import os
from dotenv import load_dotenv

load_dotenv()

# Elasticsearch Config
ES_HOST = os.getenv("ES_HOST", "http://localhost:9200")
ES_INDEX_NAME = os.getenv("ES_INDEX", "plagiarism_documents")

# gRPC Config
GRPC_PORT = os.getenv("GRPC_PORT", "50051")