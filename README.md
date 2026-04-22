#  Plagiarism Detection System

Hệ thống phát hiện đạo văn hiện đại sử dụng công nghệ **Vector Search (Semantic Search)** và **Trí tuệ nhân tạo (LLM)** để phân tích văn bản.

## Tính năng chính
- **Hybrid Search**: Kết hợp tìm kiếm Vector (ngữ nghĩa) và Lexical (từ khóa) để đạt độ chính xác cao nhất.
- **PDF Processing**: Tự động trích xuất và băm tài liệu từ file PDF.
- **AI Analysis**: Sử dụng Ollama (Llama 3.2) để giải thích chi tiết lý do đạo văn và đánh giá mức độ vi phạm.
- **MinIO Storage**: Tích hợp lưu trữ tài liệu đám mây.
- **gRPC Interface**: Hiệu suất cao, hỗ trợ streaming cho việc upload tài liệu số lượng lớn.

## Kiến trúc hệ thống
- **Backend**: Python (gRPC, Pydantic, Httpx)
- **Database**: Elasticsearch 8.x (Dense Vector search)
- **AI Engine**: Ollama (nomic-embed-text & Llama 3.2)
- **Storage**: MinIO (Object Storage)
- **UI**: Streamlit (Dashboard kiểm tra đạo văn)

## Hướng dẫn cài đặt

### 1. Yêu cầu hệ thống
- Docker & Docker Compose
- Ollama (đã tải model `nomic-embed-text` và `llama3.2`)

### 2. Chạy với Docker
```bash
# Clone dự án
cd PlagiarismDetection

# Cấu hình môi trường
cp .env.example .env
# Chỉnh sửa file .env để khớp với môi trường của bạn

# Khởi động hệ thống
docker-compose up -d --build
```

### 3. Kiểm tra hệ thống (Tests)
```bash
source env/bin/activate
python tests/test_client.py
```

## Tài liệu API
Xem chi tiết tại `docs/API.md`

## Cấu hình quan trọng (.env)
- `CHUNK_SIZE`: Độ dài đoạn văn để phân tích (Khuyên dùng: 150).
- `MIN_SCORE_THRESHOLD`: Ngưỡng báo đạo văn (Khuyên dùng: 0.6).
- `ANALYZER_MODE`: Chế độ dùng Ollama hoặc Gemini.
