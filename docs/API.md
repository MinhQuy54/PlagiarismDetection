# 📚 Plagiarism Detection API Documentation (gRPC)

Tài liệu này mô tả các dịch vụ gRPC được cung cấp bởi hệ thống Phát hiện Đạo văn.

##  servicio PlagiarismService

### 1. `CheckPlagiarism`
Kiểm tra đạo văn cho một đoạn văn bản thuần túy.

- **Request**: `PlagiarismRequest`
  - `text` (string): Nội dung văn bản cần kiểm tra.
  - `language` (string, optional): Ngôn ngữ của văn bản.
  - `include_ai_analysis` (bool): Bật phân tích ngữ nghĩa bằng Ollama/LLM.
  - `options` (CheckOptions): Cấu hình tìm kiếm (min_similarity, top_k).

- **Response**: `PlagiarismResponse`
  - `plagiarism_percentage` (float): Tỷ lệ đạo văn (0-100).
  - `severity` (string): Mức độ vi phạm (SAFE, LOW, MEDIUM, HIGH, CRITICAL).
  - `explanation` (string): Lời giải thích từ hệ thống hoặc AI.
  - `matches` (list[PlagiarismMatch]): Danh sách các đoạn trùng khớp tìm thấy.

---

### 2. `IndexPdfFromMinio`
Tải file PDF từ MinIO, trích xuất văn bản, băm nhỏ (chunking) và lưu vào cơ sở dữ liệu để làm nguồn đối chiếu.

- **Request**: `IndexPdfRequest`
  - `bucket_name` (string): Tên bucket trên MinIO.
  - `object_path` (string): Đường dẫn đến file PDF trong bucket.

- **Response**: `IndexPdfResponse`
  - `success` (bool): Trạng thái thành công.
  - `document_id` (string): ID duy nhất của tài liệu trong database.
  - `chunks_count` (int): Số lượng mảnh (chunks) đã được tạo ra.

---

### 3. `BatchUpload` (Client Streaming)
Upload nhiều tài liệu cùng một lúc theo dạng luồng dữ liệu (streaming).

- **Request**: Stream of `UploadRequest`
  - `title` (string): Tiêu đề tài liệu.
  - `content` (string): Nội dung văn bản.

- **Response**: `BatchUploadResponse`
  - `total_uploaded` (int): Tổng số tài liệu đã upload thành công.
  - `failed_count` (int): Số tài liệu bị lỗi.

---

### 4. `DeleteDocument`
Xóa tài liệu và toàn bộ các mảnh vector liên quan khỏi hệ thống.

- **Request**: `DeleteDocumentRequest`
  - `document_id` (string): ID của tài liệu cần xóa.

- **Response**: `DeleteDocumentResponse`
  - `success` (bool): Đã xóa thành công hay chưa.

---

### 5. `HealthCheck`
Kiểm tra tình trạng sức khỏe của các thành phần hệ thống.

- **Request**: `HealthCheckRequest`

- **Response**: `HealthCheckResponse`
  - `status` (string): Tình trạng chung.
  - `details` (map): Chi tiết trạng thái của Elasticsearch, Ollama, MinIO.
