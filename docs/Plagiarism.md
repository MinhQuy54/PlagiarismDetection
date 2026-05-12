# Plagiarism Detection - Tài liệu kỹ thuật

## Tổng quan

Hệ thống phát hiện đạo văn sử dụng kết hợp **Semantic Similarity** (embedding vectors) và **Lexical Similarity** (so sánh từ vựng) để đánh giá mức độ trùng lặp văn bản.

## Kiến trúc hệ thống

```
┌─────────────────────────────────────────────────────────────────┐
│                         INPUT                                   │
│              (Text hoặc PDF từ MinIO)                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    1. PREPROCESSING                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐          │
│  │  Text Input │    │  PDF Input  │    │   Filter    │          │
│  │             │    │  Extract &  │───▶│  < 200 chars│          │
│  │             │    │  Parse      │    │   skipped   │          │
│  └─────────────┘    └─────────────┘    └─────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      2. CHUNKING                                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  chunk_size: 100 words (default)                        │    │
│  │  chunk_overlap: 20 words                                │    │
│  │  min_chunk_size: 30 words                               │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
│  Input Text ──▶ [Chunk 1] [Chunk 2] [Chunk 3] ...               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     3. EMBEDDING                                │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Model: nomic-embed-text (Ollama)                       │    │
│  │  Dimensions: 768                                        │    │
│  │                                                         │    │
│  │  [Chunk 1] ──▶ [Vector 1]                               │    │
│  │  [Chunk 2] ──▶ [Vector 2]                               │    │
│  │  [Chunk 3] ──▶ [Vector 3]                               │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  4. VECTOR SEARCH                               │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Elasticsearch kNN Search                               │    │
│  │  - top_k: 10 results per chunk                          │    │
│  │  - min_score: 0.50                                      │    │
│  │  - max_results_per_source: 3                            │    │
│  │                                                         │    │
│  │  Cosine Similarity: score = cos(input_vec, db_vec)      │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│               5. COMBINED SIMILARITY                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  combined_score = (semantic × 0.5) + (lexical × 0.5)    │    │
│  │                                                         │    │
│  │  Semantic: Cosine similarity từ Elasticsearch           │    │
│  │  Lexical:  Asymmetric lexical matching                  │    │
│  │            - Containment similarity (60%)               │    │
│  │            - Sequence matching (40%)                    │    │
│  │                                                         │    │
│  │  Citation Penalty: -15% nếu có trích dẫn nguồn          │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│            6. PLAGIARISM PERCENTAGE                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  Chỉ tính các chunks có similarity >= 0.50              │    │
│  │                                                         │    │
│  │  plagiarism_% = Σ(word_count × similarity)/total_words  │    │
│  │                                                         │    │
│  │  Ví dụ:                                                 │    │
│  │  - Chunk 1: 50 words, similarity 0.95 ──▶ tính          │    │
│  │  - Chunk 2: 50 words, similarity 0.30 ──▶ bỏ qua        │    │
│  │  - Chunk 3: 50 words, similarity 0.70 ──▶ tính          │    │
│  │                                                         │    │
│  │  Result = (50×0.95 + 0 + 50×0.70) / 150 × 100 = 55%     │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    7. SEVERITY                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  CRITICAL : >= 95%  (Đạo văn nghiêm trọng)              │    │
│  │  HIGH     : >= 85%  (Đạo văn mức cao)                   │    │
│  │  MEDIUM   : >= 70%  (Nghi ngờ đạo văn)                  │    │
│  │  LOW      : >= 50%  (Có thể trùng ý tưởng)              │    │
│  │  SAFE     : < 50%   (An toàn)                           │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

## Chi tiết các bước xử lý

### 1. Preprocessing

#### Text Input (`CheckPlagiarism`)
- Nhận text trực tiếp từ request
- Normalize text: loại bỏ ký tự đặc biệt, whitespace thừa

#### PDF Input (`CheckPdfFromMinio` / `IndexPdfFromMinio`)
- Download PDF từ MinIO storage
- Sử dụng `unstructured` library để extract content
- Loại bỏ các phần không cần thiết:
  - Mục lục (TOC)
  - Header/Footer
  - Danh sách hình/bảng
- **Filter**: Bỏ qua các đoạn content < 200 ký tự

### 2. Chunking

Text được chia thành các chunks nhỏ để so sánh chính xác hơn:

| Parameter | Default | Mô tả |
|-----------|---------|-------|
| `chunk_size` | 100 words | Số từ tối đa mỗi chunk |
| `chunk_overlap` | 20 words | Số từ overlap giữa các chunks |
| `min_chunk_size` | 30 words | Chunk nhỏ hơn sẽ bị bỏ qua |

**Ví dụ:**
```
Input: 250 words
→ Chunk 0: words 0-99 (100 words)
→ Chunk 1: words 80-179 (100 words, overlap 20)
→ Chunk 2: words 160-249 (90 words)
```

### 3. Embedding

Sử dụng **Ollama** với model `nomic-embed-text`:
- Chuyển text thành vector 768 chiều
- Batch processing để tối ưu performance
- Vector được sử dụng cho semantic search

### 4. Vector Search (Elasticsearch)

```json
{
  "knn": {
    "field": "embedding",
    "query_vector": [...],
    "k": 10,
    "num_candidates": 100
  }
}
```

**Parameters:**
- `top_k`: Số kết quả tối đa (default: 10)
- `min_score`: Ngưỡng similarity tối thiểu (default: 0.50)
- `max_results_per_source`: Giới hạn kết quả từ 1 document (default: 3)

### 5. Combined Similarity

Kết hợp 2 phương pháp để giảm false positives:

#### Semantic Similarity (50%)
- Cosine similarity giữa embedding vectors
- Capture ý nghĩa ngữ cảnh

#### Lexical Similarity (50%)
- **Asymmetric matching**: Xử lý trường hợp input dài hơn matched text
- **Containment**: % từ của matched text có trong input
- **Sequence matching**: So sánh chuỗi ký tự

```python
# Nếu input ngắn hơn 70% matched → dùng symmetric
# Nếu input dài hơn → dùng asymmetric (containment)

if len_ratio > 0.7:
    lexical = symmetric_similarity()
else:
    lexical = containment * 0.6 + sequence * 0.4
```

#### Citation Detection
Nếu văn bản có trích dẫn nguồn (ví dụ: `(Nguyen, 2024)`), giảm 15% điểm.

### 6. Plagiarism Percentage

**Công thức:**
```
plagiarism_% = Σ(word_count_i × similarity_i) / total_words × 100
```

Chỉ tính các chunks có `similarity >= 0.50` (threshold `similarity_low`).

**Ví dụ:**
| Chunk | Words | Similarity | Tính? |
|-------|-------|------------|-------|
| 0 | 50 | 0.95 | ✓ (50 × 0.95 = 47.5) |
| 1 | 50 | 0.30 | ✗ (bỏ qua) |
| 2 | 50 | 0.70 | ✓ (50 × 0.70 = 35) |

**Kết quả:** (47.5 + 35) / 150 × 100 = **55%**

### 7. Severity Levels

| Level | Threshold | Mô tả |
|-------|-----------|-------|
| `CRITICAL` | >= 95% | Đạo văn nghiêm trọng |
| `HIGH` | >= 85% | Đạo văn mức cao |
| `MEDIUM` | >= 70% | Nghi ngờ đạo văn |
| `LOW` | >= 50% | Có thể trùng ý tưởng |
| `SAFE` | < 50% | An toàn |

## API Endpoints

### CheckPlagiarism (Text)

```protobuf
rpc CheckPlagiarism(CheckRequest) returns (CheckResponse)
```

**Request:**
```json
{
  "text": "Văn bản cần kiểm tra...",
  "options": {
    "min_similarity": 0.5,
    "top_k": 10,
    "include_ai_analysis": false,
    "exclude_docs": ["doc-id-1"]
  }
}
```

### CheckPdfFromMinio (PDF)

```protobuf
rpc CheckPdfFromMinio(CheckPdfFromMinioRequest) returns (CheckPdfFromMinioResponse)
```

**Request:**
```json
{
  "bucket_name": "lvtn",
  "object_path": "documents/thesis.pdf",
  "options": {
    "min_similarity": 0.5,
    "top_k": 10
  }
}
```

### IndexPdfFromMinio (Index PDF)

```protobuf
rpc IndexPdfFromMinio(IndexPdfFromMinioRequest) returns (IndexPdfFromMinioResponse)
```

**Request:**
```json
{
  "bucket_name": "lvtn",
  "object_path": "documents/reference.pdf",
  "title": "Tài liệu tham khảo",
  "metadata": {
    "author": "Nguyen Van A",
    "year": "2024"
  }
}
```

## Response Structure

```json
{
  "request_id": "uuid",
  "plagiarism_percentage": 73.5,
  "severity": "MEDIUM",
  "explanation": "Nghi ngờ đạo văn. 3 đoạn văn có nội dung tương tự...",
  "matches": [
    {
      "document_id": "doc-123",
      "document_title": "Tài liệu gốc",
      "matched_text": "Đoạn văn trùng khớp trong DB...",
      "input_text": "Đoạn văn input...",
      "similarity_score": 0.95,
      "position": {
        "start": 0,
        "end": 320,
        "chunk_index": 0
      }
    }
  ],
  "chunks": [
    {
      "chunk_index": 0,
      "text": "Nội dung chunk...",
      "max_similarity": 0.95,
      "status": "CRITICAL",
      "best_match_doc_id": "doc-123"
    }
  ],
  "metadata": {
    "processing_time_ms": 2500,
    "chunks_analyzed": 5,
    "documents_searched": 100
  }
}
```

## Configuration

### Environment Variables

```env
# Text Chunking
CHUNK_SIZE=100
CHUNK_OVERLAP=20
MIN_CHUNK_SIZE=30

# Search
TOP_K_RESULTS=10
MIN_SCORE_THRESHOLD=0.50
MAX_RESULTS_PER_SOURCE=3

# Similarity Thresholds
SIMILARITY_CRITICAL=0.95
SIMILARITY_HIGH=0.85
SIMILARITY_MEDIUM=0.70
SIMILARITY_LOW=0.50

# Embedding
EMBEDDING_DIMS=768
OLLAMA_EMBED_MODEL=nomic-embed-text
```

### PDF Processing

```python
# Minimum content length để index (chars)
MIN_CONTENT_LENGTH = 200

# Các tiêu đề bị loại trừ
EXCLUDED_TITLES = [
    "MỤC LỤC", "DANH SÁCH", "DANH MỤC",
    "TABLE OF CONTENTS", "TÀI LIỆU THAM KHẢO"
]
```

## Ví dụ thực tế

### Input
```
"3.2.1 Mô tả chức năng Chức năng Withdraw Money cho phép
khách hàng rút tiền từ tài khoản của mình. Sau khi Customer
đăng nhập và chọn tài khoản, họ có thể vào tab Withdrawl..."
```

### Process
1. **Chunking**: 1 chunk (67 words < 100)
2. **Embedding**: Vector 768 chiều
3. **Search**: Tìm được 3 chunks tương tự trong DB
4. **Combined Score**:
   - Semantic: 99.83%
   - Lexical: 100%
   - Combined: 99.9%
5. **Percentage**: 99.9%
6. **Severity**: CRITICAL

### Output
```json
{
  "plagiarism_percentage": 99.9,
  "severity": "CRITICAL",
  "explanation": "Phát hiện đạo văn nghiêm trọng..."
}
```

## Lưu ý

1. **Chunk size nhỏ hơn = chính xác hơn** nhưng tốn nhiều embedding calls
2. **Asymmetric matching** giúp phát hiện khi input chứa nhiều nội dung hơn matched text
3. **Citation detection** giảm false positive khi văn bản có trích dẫn đúng cách
4. **Content < 200 chars** bị bỏ qua để tránh noise từ header/footer/caption