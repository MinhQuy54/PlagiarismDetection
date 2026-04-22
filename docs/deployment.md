# 🚢 Deployment Guide

Tài liệu này hướng dẫn cách triển khai hệ thống Phát hiện Đạo văn lên môi trường Production.

## 1. Cấu hình Production (.env)
Khi chạy thực tế, hãy đảm bảo các thông số sau được tối ưu:

```env
# Logging: Để WARNING hoặc ERROR để giảm tải dung lượng log
LOG_LEVEL=WARNING

# gRPC: Tăng số lượng Worker để xử lý đồng thời tốt hơn
GRPC_MAX_WORKERS=20

# Elasticsearch: Cấu hình RAM phù hợp (Mac M1/M2: 2GB+, Server: 4GB+)
ES_JAVA_OPTS="-Xms2g -Xmx2g"
```

## 2. Bảo mật (Security)
- **Cấp quyền Elasticsearch**: Trong môi trường Production, hãy bật `xpack.security.enabled=true` và cấu hình `ES_USER` / `ES_PASSWORD`.
- **TLS/SSL**: Bật `GRPC_TLS_ENABLED=true` và cung cấp đường dẫn đến các file chứng chỉ trong thư mục `certs/` để mã hóa đường truyền gRPC.

## 3. Data Persistence (Lưu trữ dữ liệu)
Đảm bảo các Volumes trong `docker-compose.yml` được mount đúng cách để không mất dữ liệu khi restart container:
- `es_data`: Lưu database Elasticsearch.
- `minio_data`: Lưu file PDF trên MinIO.

## 4. Tối ưu hóa hiệu suất
- **Embeddings**: Nếu số lượng tài liệu cực lớn, hãy cân nhắc dùng Model GPU cho Ollama (nếu dùng card NVIDIA) để tăng tốc độ tạo vector.
- **Elasticsearch**: Định kỳ thực hiện `force merge` cho các index cũ để tăng tốc độ tìm kiếm.

## 5. Giám sát (Monitoring)
- Hệ thống hỗ trợ Prometheus Metrics trên cổng `:9107`.
- Bạn có thể dùng **Kibana** (cổng `:5601`) để theo dõi các bản ghi đạo văn trực quan.
