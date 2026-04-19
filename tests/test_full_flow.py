import time
from src.core.document_manager import get_document_manager
from src.core.detector import get_detector
from src.storage.elasticsearch import get_es_client

def test_integration():
    es_client = get_es_client()
    es_client.create_index(force=True)
    doc_manager = get_document_manager()
    detector = get_detector()

    # Bước 1: Nạp dữ liệu mẫu (Seeding)
    print("--- 1. Đang nạp tài liệu mẫu vào kho ---")
    content_goc = """
    Trí tuệ nhân tạo (AI) là một ngành của khoa học máy tính liên quan đến việc xây dựng các máy móc thông minh 
    có khả năng thực hiện các nhiệm vụ đòi hỏi trí tuệ con người. Học máy là một tập con của AI.
    """
    upload_res = doc_manager.upload_document(
        title="Tài liệu gốc về AI",
        content=content_goc,
        metadata={"author": "Quý Ngô"}
    )
    
    if not upload_res.success:
        print("Lỗi nạp tài liệu!")
        return

    print(f"✅ Đã nạp xong bài gốc. ID: {upload_res.document_id}")
    time.sleep(2) # Đợi ES index dữ liệu

    # Bước 2: Kiểm tra đạo văn với một nội dung tương tự (Paraphrased)
    print("\n--- 2. Đang kiểm tra đạo văn đoạn văn nghi vấn ---")
    query_text = "Học máy là một phần nhỏ của trí tuệ nhân tạo. AI là lĩnh vực máy tính tạo ra máy thông minh."
    
    result = detector.check_plagiarism(query_text)
    
    # Bước 3: Hiển thị kết quả
    print(f"\n📊 TỶ LỆ ĐẠO VĂN: {result.plagiarism_percentage}%")
    print(f"⚠️ MỨC ĐỘ: {result.severity}")
    print(f"📝 GIẢI THÍCH AI: {result.explanation}")
    
    if result.chunk_analysis:
        print("\n🔍 CHI TIẾT CÁC ĐOẠN TRÙNG LẶP:")
        for res in result.chunk_analysis:
            print(f"- Đoạn nghi vấn: {res.text}")
            for match in res.matches:
                print(f"  + Khớp với nguồn: {match.document_title}")
                print(f"  + Độ tương đồng vector: {match.similarity_score:.2f}")

if __name__ == "__main__":
    test_integration()