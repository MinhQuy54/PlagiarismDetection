# Plagiarism Detection System - Architecture Document

## 1. Tổng quan hệ thống

Hệ thống phát hiện đạo văn hiện đại sử dụng kết hợp:
- **Elasticsearch**: Lưu trữ văn bản và vector embedding (Sử dụng kiến trúc Flat Indexing).
- **Ollama**: Tạo embedding vectors và AI kết luận cuối cùng.
- **gRPC**: Giao thức truyền tải dữ liệu API hiệu suất cao.

### 1.1 Flow xử lý (Logic Flow)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐     ┌─────────────┐
│   Client    │────▶│  gRPC API   │────▶│  Plagiarism     │────▶│ Elasticsearch│
│  (Text/PDF) │     │  Service    │     │  Engine         │     │  (Storage)   │
└─────────────┘     └─────────────┘     └─────────────────┘     └─────────────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │   Ollama    │
                                        │ (Embedding  │
                                        │  + AI)      │
                                        └─────────────┘
```

## 2. Các thành phần chính

### 2.1 gRPC Service (`src/service/`)
- **CheckPlagiarism**: Kiểm tra đạo văn (Hỗ trợ Text thuần và PDF từ MinIO).
- **IndexPdfFromMinio**: Tải và băm tài liệu từ MinIO vào database.
- **BatchUpload**: Streaming nạp tài liệu metadata.
- **HealthCheck**: Giám sát Elasticsearch, Ollama, MinIO.

### 2.2 Elasticsearch Index (Verified Mapping)
Hệ thống sử dụng cơ chế lưu trữ phẳng (Flat) thay vì Nested để tối ưu kNN search:

**Index 1: `plagiarism_documents`** (Metadata)
**Index 2: `plagiarism_documents_chunks`** (Vector Data):
```json
{
  "properties": {
    "document_id": { "type": "keyword" },
    "chunk_id": { "type": "keyword" },
    "text": { "type": "text" },
    "embedding": {
      "type": "dense_vector",
      "dims": 768,
      "index": true,
      "similarity": "cosine"
    },
    "position": { "type": "integer" }
  }
}
```

### 2.3 Ollama Models
- **Embedding**: `nomic-embed-text` (768 dims).
- **AI Analysis**: `llama3.2` (Chịu trách nhiệm giải thích ngữ nghĩa).

## 3. Ngưỡng phát hiện đạo văn (Thresholds)

### 3.1 Similarity Levels
| Level | Cosine Similarity | Mô tả |
|-------|-------------------|-------|
| **CRITICAL** | >= 0.95 | Copy nguyên văn, đạo văn nghiêm trọng |
| **HIGH** | 0.85 - 0.94 | Đạo văn cao, paraphrase nhẹ |
| **MEDIUM** | 0.70 - 0.84 | Nghi ngờ đạo văn, paraphrase nhiều |
| **LOW** | 0.50 - 0.69 | Có thể trùng ý tưởng |
| **SAFE** | < 0.50 | An toàn, không đạo văn |

### 3.2 Chunk Configuration
- **Chunk size**: 150 từ (Tối ưu cho semantic search).
- **Overlap**: 20 từ.
- **Min chunk**: 50 từ.

## 4. Tính % đạo văn cuối cùng

### 4.1 Thuật toán kết hợp
Hệ thống sử dụng tỷ lệ từ văn bản bị trùng (weighted by similarity) và sau đó sử dụng Ollama để "tinh chỉnh" con số cuối cùng dựa trên bối cảnh:
```python
# Điểm số = Tổng (Từ trong mảnh * Similarity) / Tổng số từ
final_percentage = ollama_analyze(text, matches, base_percentage)
```

## 5. Cấu trúc thư mục Project (Verified Tree)

```
PlagiarismDetection/
├── proto/
│   └── plagiarism.proto          # gRPC definitions
├── src/
│   ├── server.py                 # Entry point
│   ├── service/                  # gRPC Implementation
│   │   └── plagiarism_service.py
│   ├── core/                     # Logic nghiệp vụ
│   │   ├── detector.py           # Bộ máy phát hiện đạo văn
│   │   ├── chunker.py            # Chia đoạn văn bản
│   │   ├── analyzer.py           # Ollama AI Agent
│   │   ├── processor.py          # Xử lý PDF
│   │   ├── document_manager.py   # Quản lý vòng đời tài liệu
│   │   └── lexical_matcher.py    # So khớp từ vựng
│   ├── storage/                  # Lưu trữ
│   │   ├── elasticsearch.py      # ES Client (kNN search)
│   │   └── minio_client.py       # MinIO Client
│   ├── embedding/                # AI Vectorization
│   │   └── ollama_embed.py
│   ├── metrics/                  # Giám sát & Interceptors
│   ├── logger/                   # Logging & Tracing
│   ├── ui/                       # Giao diện Dashbord
│   │   └── app.py (Streamlit)
│   └── plagiarism_pb2*.py        # Generated gRPC code
├── tests/                        # Hệ thống kiểm thử
│   ├── test_client.py            # Integration test chính
│   ├── test_detector.py          # Unit test bộ máy chính
│   ├── test_analyze.py           # Test khả năng suy luận của AI
│   └── integration/              # Test kết nối hạ tầng
├── scripts/
│   └── generate_proto.sh
├── docker-compose.yml
├── Dockerfile
└── .env                          # Cấu hình môi trường
```

## 6. Dependencies
- `grpcio`, `elasticsearch8`, `pydantic`, `httpx`, `pypdf`, `langdetect`.

## 7. Environment Variables
- `ES_HOST`, `OLLAMA_HOST`, `MINIO_HOST`, `CHUNK_SIZE=150`, `MIN_SCORE_THRESHOLD=0.6`.
