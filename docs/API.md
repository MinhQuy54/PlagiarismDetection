# Plagiarism Detection Service - API Documentation

## Tổng quan

Service sử dụng **gRPC** protocol. Mặc định chạy tại `localhost:50051`.

## Cách kết nối

### Python
```python
import grpc
from src import plagiarism_pb2, plagiarism_pb2_grpc

# Tạo channel và stub
channel = grpc.insecure_channel('localhost:50051')
stub = plagiarism_pb2_grpc.PlagiarismServiceStub(channel)
```

---

## 1. CheckPlagiarism - Kiểm tra đạo văn

Kiểm tra một đoạn văn bản có đạo văn hay không.

### Request: `CheckRequest`

| Field | Type | Bắt buộc | Mô tả |
|-------|------|----------|-------|
| `text` | string | ✅ | Văn bản cần kiểm tra đạo văn |
| `options` | CheckOptions | ❌ | Các tùy chọn (xem bên dưới) |

#### CheckOptions (tùy chọn)

| Field | Type | Default | Mô tả |
|-------|------|---------|-------|
| `min_similarity` | float | 0.5 | Ngưỡng similarity tối thiểu (0.0 - 1.0) |
| `top_k` | int32 | 10 | Số kết quả tương tự tối đa trả về |
| `include_ai_analysis` | bool | true | Bật/tắt AI analysis (tắt = nhanh hơn) |
| `exclude_docs` | string[] | [] | Danh sách document_id không muốn so sánh |

### Response: `CheckResponse`

| Field | Type | Mô tả |
|-------|------|-------|
| `request_id` | string | ID của request (UUID) |
| `plagiarism_percentage` | float | Phần trăm đạo văn (0-100) |
| `severity` | Severity | Mức độ nghiêm trọng |
| `explanation` | string | Giải thích kết quả (tiếng Việt) |
| `matches` | Match[] | Danh sách các đoạn trùng khớp |
| `chunks` | ChunkAnalysis[] | Phân tích từng chunk |
| `metadata` | Metadata | Thông tin xử lý |

#### Severity (Mức độ)

| Value | Enum | Mô tả |
|-------|------|-------|
| 0 | SAFE | An toàn (< 50%) |
| 1 | LOW | Thấp (50-69%) |
| 2 | MEDIUM | Trung bình (70-84%) |
| 3 | HIGH | Cao (85-94%) |
| 4 | CRITICAL | Nghiêm trọng (>= 95%) |

#### Match (Kết quả trùng khớp)

| Field | Type | Mô tả |
|-------|------|-------|
| `document_id` | string | ID của document nguồn |
| `document_title` | string | Tiêu đề document nguồn |
| `matched_text` | string | Đoạn văn trùng khớp từ nguồn |
| `input_text` | string | Đoạn văn input bị trùng |
| `similarity_score` | float | Độ tương đồng (0.0 - 1.0) |
| `position` | Position | Vị trí trong văn bản input |

#### Metadata

| Field | Type | Mô tả |
|-------|------|-------|
| `processing_time_ms` | int64 | Thời gian xử lý (milliseconds) |
| `chunks_analyzed` | int32 | Số chunks đã phân tích |
| `documents_searched` | int32 | Số documents trong database |

### Ví dụ Python

```python
# Kiểm tra đạo văn cơ bản
response = stub.CheckPlagiarism(
    plagiarism_pb2.CheckRequest(
        text="Văn bản cần kiểm tra đạo văn ở đây..."
    ),
    timeout=300  # 5 phút timeout
)

print(f"Đạo văn: {response.plagiarism_percentage:.1f}%")
print(f"Mức độ: {response.severity}")  # 0=SAFE, 1=LOW, 2=MEDIUM, 3=HIGH, 4=CRITICAL
print(f"Giải thích: {response.explanation}")

# Xem các đoạn trùng khớp
for match in response.matches:
    print(f"- Nguồn: {match.document_title}")
    print(f"  Độ tương đồng: {match.similarity_score:.1%}")
    print(f"  Đoạn trùng: {match.matched_text[:100]}...")
```

```python
# Kiểm tra với tùy chọn
response = stub.CheckPlagiarism(
    plagiarism_pb2.CheckRequest(
        text="Văn bản cần kiểm tra...",
        options=plagiarism_pb2.CheckOptions(
            min_similarity=0.7,      # Chỉ lấy kết quả >= 70%
            top_k=5,                 # Tối đa 5 kết quả
            exclude_docs=["doc-123"] # Bỏ qua document này
        )
    )
)
```

---

## 2. UploadDocument - Upload tài liệu

Thêm một tài liệu vào database để so sánh đạo văn.

### Request: `UploadRequest`

| Field | Type | Bắt buộc | Mô tả |
|-------|------|----------|-------|
| `title` | string | ✅ | Tiêu đề tài liệu |
| `content` | string | ✅ | Nội dung tài liệu (plain text) |
| `metadata` | map<string,string> | ❌ | Thông tin bổ sung (author, year...) |
| `language` | string | ❌ | Ngôn ngữ: "vi", "en", hoặc "auto" |

### Response: `UploadResponse`

| Field | Type | Mô tả |
|-------|------|-------|
| `document_id` | string | ID của document (UUID) |
| `title` | string | Tiêu đề |
| `chunks_created` | int32 | Số chunks đã tạo |
| `message` | string | Thông báo kết quả |
| `success` | bool | Upload thành công hay không |

### Ví dụ Python

```python
# Upload một tài liệu
response = stub.UploadDocument(
    plagiarism_pb2.UploadRequest(
        title="Luận văn về Machine Learning",
        content="""
        Machine Learning là một nhánh của trí tuệ nhân tạo...
        (nội dung đầy đủ ở đây)
        """,
        metadata={
            "author": "Nguyen Van A",
            "year": "2024",
            "university": "HCMUT"
        },
        language="vi"
    )
)

if response.success:
    print(f"Upload thành công!")
    print(f"Document ID: {response.document_id}")
    print(f"Số chunks: {response.chunks_created}")
else:
    print(f"Lỗi: {response.message}")
```

---

## 3. BatchUpload - Upload nhiều tài liệu (Streaming)

Upload nhiều tài liệu cùng lúc sử dụng gRPC streaming.

### Request: Stream of `UploadRequest`

Gửi nhiều `UploadRequest` liên tiếp.

### Response: `BatchUploadResponse`

| Field | Type | Mô tả |
|-------|------|-------|
| `total_documents` | int32 | Tổng số documents |
| `successful` | int32 | Số thành công |
| `failed` | int32 | Số thất bại |
| `results` | UploadResult[] | Chi tiết từng document |

### Ví dụ Python

```python
def generate_documents():
    """Generator để stream documents."""
    documents = [
        {"title": "Doc 1", "content": "Nội dung 1..."},
        {"title": "Doc 2", "content": "Nội dung 2..."},
        {"title": "Doc 3", "content": "Nội dung 3..."},
    ]
    for doc in documents:
        yield plagiarism_pb2.UploadRequest(
            title=doc["title"],
            content=doc["content"]
        )

# Batch upload
response = stub.BatchUpload(generate_documents())

print(f"Tổng: {response.total_documents}")
print(f"Thành công: {response.successful}")
print(f"Thất bại: {response.failed}")
```

---

## 4. GetDocument - Lấy thông tin tài liệu

Lấy thông tin chi tiết của một tài liệu theo ID.

### Request: `GetDocumentRequest`

| Field | Type | Bắt buộc | Mô tả |
|-------|------|----------|-------|
| `document_id` | string | ✅ | ID của document |
| `include_content` | bool | ❌ | Có lấy nội dung đầy đủ không (default: false) |
| `include_chunks` | bool | ❌ | Có lấy chi tiết chunks không (default: false) |

### Response: `GetDocumentResponse`

| Field | Type | Mô tả |
|-------|------|-------|
| `document` | Document | Thông tin document |
| `found` | bool | Tìm thấy hay không |

#### Document

| Field | Type | Mô tả |
|-------|------|-------|
| `document_id` | string | ID |
| `title` | string | Tiêu đề |
| `content` | string | Nội dung (nếu include_content=true) |
| `metadata` | map<string,string> | Thông tin bổ sung |
| `language` | string | Ngôn ngữ |
| `chunk_count` | int32 | Số chunks |
| `chunks` | Chunk[] | Chi tiết chunks (nếu include_chunks=true) |
| `created_at` | string | Thời gian tạo |

### Ví dụ Python

```python
# Lấy thông tin cơ bản
response = stub.GetDocument(
    plagiarism_pb2.GetDocumentRequest(
        document_id="abc-123-xyz"
    )
)

if response.found:
    doc = response.document
    print(f"Tiêu đề: {doc.title}")
    print(f"Ngôn ngữ: {doc.language}")
    print(f"Số chunks: {doc.chunk_count}")
else:
    print("Không tìm thấy document")

# Lấy đầy đủ nội dung
response = stub.GetDocument(
    plagiarism_pb2.GetDocumentRequest(
        document_id="abc-123-xyz",
        include_content=True,
        include_chunks=True
    )
)
```

---

## 5. DeleteDocument - Xóa tài liệu

Xóa một tài liệu khỏi database.

### Request: `DeleteDocumentRequest`

| Field | Type | Bắt buộc | Mô tả |
|-------|------|----------|-------|
| `document_id` | string | ✅ | ID của document cần xóa |

### Response: `DeleteDocumentResponse`

| Field | Type | Mô tả |
|-------|------|-------|
| `success` | bool | Xóa thành công hay không |
| `message` | string | Thông báo |

### Ví dụ Python

```python
response = stub.DeleteDocument(
    plagiarism_pb2.DeleteDocumentRequest(
        document_id="abc-123-xyz"
    )
)

if response.success:
    print("Đã xóa document")
else:
    print(f"Lỗi: {response.message}")
```

---

## 6. SearchDocuments - Tìm kiếm tài liệu

Tìm kiếm tài liệu trong database theo từ khóa hoặc metadata.

### Request: `SearchRequest`

| Field | Type | Bắt buộc | Mô tả |
|-------|------|----------|-------|
| `query` | string | ❌ | Từ khóa tìm kiếm |
| `filters` | map<string,string> | ❌ | Lọc theo metadata |
| `limit` | int32 | ❌ | Số kết quả tối đa (default: 10) |
| `offset` | int32 | ❌ | Bỏ qua N kết quả đầu (pagination) |

### Response: `SearchResponse`

| Field | Type | Mô tả |
|-------|------|-------|
| `documents` | DocumentSummary[] | Danh sách documents |
| `total` | int32 | Tổng số kết quả |

### Ví dụ Python

```python
# Tìm theo từ khóa
response = stub.SearchDocuments(
    plagiarism_pb2.SearchRequest(
        query="Machine Learning",
        limit=10
    )
)

print(f"Tìm thấy: {response.total} documents")
for doc in response.documents:
    print(f"- {doc.title} ({doc.chunk_count} chunks)")

# Tìm theo metadata
response = stub.SearchDocuments(
    plagiarism_pb2.SearchRequest(
        filters={"author": "Nguyen Van A", "year": "2024"},
        limit=20,
        offset=0
    )
)
```

---

## 7. HealthCheck - Kiểm tra trạng thái service

Kiểm tra xem service và các thành phần có hoạt động bình thường không.

### Request: `HealthCheckRequest`

Không có field nào.

### Response: `HealthCheckResponse`

| Field | Type | Mô tả |
|-------|------|-------|
| `healthy` | bool | Service có healthy không |
| `details` | map<string, string> | Trạng thái từng component (vd: {"ollama": "up"}) |

### Ví dụ Python

```python
response = stub.HealthCheck(plagiarism_pb2.HealthCheckRequest())

print(f"Service healthy: {response.healthy}")

for name, status in response.details.items():
    icon = "✅" if status == "up" or status == "Available" else "❌"
    print(f"  {icon} {name}: {status}")
```

---

## Ví dụ hoàn chỉnh

```python
#!/usr/bin/env python3
"""Ví dụ sử dụng Plagiarism Detection Service."""

import grpc
from src import plagiarism_pb2, plagiarism_pb2_grpc


def main():
    # 1. Kết nối
    channel = grpc.insecure_channel('localhost:50051')
    stub = plagiarism_pb2_grpc.PlagiarismServiceStub(channel)

    # 2. Kiểm tra health
    health = stub.HealthCheck(plagiarism_pb2.HealthCheckRequest())
    if not health.healthy:
        print("Service không healthy!")
        return

    # 3. Upload tài liệu gốc
    upload_resp = stub.UploadDocument(
        plagiarism_pb2.UploadRequest(
            title="Bài viết gốc về AI",
            content="""
            Trí tuệ nhân tạo (AI) là một lĩnh vực của khoa học máy tính
            tập trung vào việc tạo ra các máy móc thông minh có khả năng
            thực hiện các nhiệm vụ thường đòi hỏi trí thông minh của con người.
            """,
            metadata={"author": "Admin", "type": "original"}
        )
    )
    print(f"Uploaded: {upload_resp.document_id}")

    # 4. Kiểm tra đạo văn
    check_resp = stub.CheckPlagiarism(
        plagiarism_pb2.CheckRequest(
            text="""
            AI là một lĩnh vực của khoa học máy tính tập trung vào
            việc tạo ra các máy móc thông minh.
            """
        ),
        timeout=300
    )

    print(f"\n=== KẾT QUẢ ===")
    print(f"Đạo văn: {check_resp.plagiarism_percentage:.1f}%")

    severity_names = ["SAFE", "LOW", "MEDIUM", "HIGH", "CRITICAL"]
    print(f"Mức độ: {severity_names[check_resp.severity]}")
    print(f"Giải thích: {check_resp.explanation}")

    if check_resp.matches:
        print(f"\nTrùng với {len(check_resp.matches)} nguồn:")
        for m in check_resp.matches[:3]:
            print(f"  - {m.document_title}: {m.similarity_score:.1%}")


if __name__ == "__main__":
    main()
```

---

## Xử lý lỗi

### gRPC Status Codes

| Code | Ý nghĩa |
|------|---------|
| `OK` | Thành công |
| `INTERNAL` | Lỗi server (xem details) |
| `INVALID_ARGUMENT` | Tham số không hợp lệ |
| `NOT_FOUND` | Không tìm thấy resource |
| `DEADLINE_EXCEEDED` | Timeout |

### Ví dụ xử lý lỗi

```python
try:
    response = stub.CheckPlagiarism(
        plagiarism_pb2.CheckRequest(text="..."),
        timeout=300
    )
except grpc.RpcError as e:
    print(f"Error code: {e.code()}")
    print(f"Details: {e.details()}")
```

---

## Tips

1. **Timeout**: Đặt timeout dài (300s) khi bật AI analysis
2. **Batch upload**: Dùng `BatchUpload` khi có nhiều documents
3. **Exclude docs**: Dùng `exclude_docs` để bỏ qua self-plagiarism
4. **Pagination**: Dùng `limit` và `offset` khi search nhiều kết quả
