import uuid
from datetime import datetime
from src.storage.elasticsearch import es_manager

def test_full_es_flow():
    print("--- 🛡️  STARTING ES CRUD TEST 🛡️  ---")

    # 1. Kiểm tra kết nối
    if not es_manager.check_health():
        print("❌ Lỗi: Không thể kết nối Elasticsearch!")
        return

    print("✅ Kết nối ES: OK")

    # 2. Khởi tạo Index (Mapping)
    es_manager.create_index()

    # 3. Giả lập dữ liệu đã băm (Chunks)
    # Giả sử ta băm 1 tài liệu thành 2 đoạn (chunks)
    doc_id = str(uuid.uuid4()) # Tạo ID duy nhất cho tài liệu
    
    # Vector giả lập 768 chiều (toàn số 0.1 và 0.2 để test)
    fake_vector_1 = [0.1] * 768
    fake_vector_2 = [0.2] * 768

    chunks_to_insert = [
        {
            "document_id": doc_id,
            "chunk_id": f"{doc_id}_1",
            "content": "Lập trình Python rất mạnh mẽ trong việc xử lý dữ liệu.",
            "vector": fake_vector_1,
            "metadata": {"author": "Minh Quy", "page": 1}
        },
        {
            "document_id": doc_id,
            "chunk_id": f"{doc_id}_2",
            "content": "Elasticsearch hỗ trợ tìm kiếm vector cực nhanh.",
            "vector": fake_vector_2,
            "metadata": {"author": "Minh Quy", "page": 1}
        }
    ]

    # 4. Test CREATE (Bulk Insert)
    print(f"🚀 Đang nạp {len(chunks_to_insert)} đoạn văn bản vào ES...")
    success_count = es_manager.bulk_index_chunks(chunks_to_insert)
    if success_count > 0:
        print(f"✅ Đã nạp thành công {success_count} đoạn.")
    else:
        print("❌ Lỗi: Không thể nạp dữ liệu!")
        return

    # 5. Test READ (Vector Search)
    print("🔍 Đang tìm kiếm thử bằng Vector tương đồng...")
    # Thử tìm bằng một vector gần giống fake_vector_1
    search_results = es_manager.vector_search(query_vector=fake_vector_1, top_k=1)
    
    if search_results:
        top_hit = search_results[0]
        print(f"✅ Đã tìm thấy kết quả khớp nhất!")
        print(f"   - Nội dung: {top_hit['_source']['content']}")
        print(f"   - Score: {top_hit['_score']}")
    else:
        print("❌ Lỗi: Không tìm thấy kết quả nào sau khi insert!")

    # 6. Test DELETE
    print(f"🗑️  Đang xóa toàn bộ dữ liệu của document_id: {doc_id}...")
    delete_res = es_manager.delete_by_document_id(doc_id)
    if delete_res and delete_res['deleted'] > 0:
        print(f"✅ Đã xóa sạch {delete_res['deleted']} đoạn của tài liệu này.")
    else:
        print("❌ Lỗi: Xóa không thành công!")

    print("--- 🏁 TEST COMPLETED SUCCESSFULLY 🏁 ---")

if __name__ == "__main__":
    test_full_es_flow()