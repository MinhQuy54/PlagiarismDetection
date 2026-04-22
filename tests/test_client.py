#!/usr/bin/env python3
"""Comprehensive Test client for Plagiarism Detection Service."""

import sys
import os
import time
import grpc
from typing import List

# Add project root to sys.path
sys.path.insert(0, ".")

from src import plagiarism_pb2, plagiarism_pb2_grpc


def get_stub():
    """Get gRPC stub with configurable host/port."""
    host = os.getenv("GRPC_HOST", "localhost")
    port = os.getenv("GRPC_PORT", "50051")
    channel = grpc.insecure_channel(f"{host}:{port}")
    return plagiarism_pb2_grpc.PlagiarismServiceStub(channel)


def test_health_check():
    """Test 1: Health check."""
    print("\n" + "=" * 50)
    print("TEST 1: Health Check")
    print("=" * 50)

    stub = get_stub()
    try:
        response = stub.HealthCheck(plagiarism_pb2.HealthCheckRequest())
        print(f"Healthy: {response.healthy}")
        for name, status in response.details.items():
            print(f"  - {name}: {status}")
        return response.healthy
    except Exception as e:
        print(f"❌ Health Check failed: {e}")
        return False


def test_batch_upload():
    """Test 2: Batch upload using stream."""
    print("\n" + "=" * 50)
    print("TEST 2: Batch Upload (Streaming)")
    print("=" * 50)

    stub = get_stub()

    def request_generator():
        docs = [
            {"title": "Batch Doc 1", "content": "Nội dung tài liệu batch số 1 dùng để kiểm tra tính năng streaming."},
            {"title": "Batch Doc 2", "content": "Nội dung tài liệu batch số 2, giúp hệ thống xử lý nhiều file cùng lúc."},
        ]
        for doc in docs:
            yield plagiarism_pb2.UploadRequest(
                title=doc["title"],
                content=doc["content"],
                metadata={"type": "test_batch", "env": "local"}
            )

    try:
        response = stub.BatchUpload(request_generator())
        print(f"Total: {response.total_documents}")
        print(f"✅ Successful: {response.successful}")
        print(f"❌ Failed: {response.failed}")
        return response.successful > 0
    except Exception as e:
        print(f"❌ Batch Upload failed: {e}")
        return False


def test_document_lifecycle():
    """Test 3: Upload -> Get -> Delete sequence."""
    print("\n" + "=" * 50)
    print("TEST 3: Document Lifecycle (Upload -> Get -> Delete)")
    print("=" * 50)

    stub = get_stub()
    
    # 1. Upload
    upload_res = stub.UploadDocument(plagiarism_pb2.UploadRequest(
        title="Lifecycle Test Doc",
        content="Đây là tài liệu dùng để test vòng đời: Tạo ra, Tìm thấy, và Xóa đi.",
        metadata={"temp": "true"}
    ))
    doc_id = upload_res.document_id
    print(f"1. Uploaded Doc ID: {doc_id}")

    # 2. Get & Verify
    get_res = stub.GetDocument(plagiarism_pb2.GetDocumentRequest(document_id=doc_id))
    if get_res.found:
        print(f"2. Found Doc: {get_res.document.title} (OK)")
    else:
        print("2. ❌ Document not found after upload")
        return False

    # 3. Delete
    del_res = stub.DeleteDocument(plagiarism_pb2.DeleteDocumentRequest(document_id=doc_id))
    print(f"3. Delete Status: {del_res.success} - {del_res.message}")

    # 4. Final Verify
    verify_res = stub.GetDocument(plagiarism_pb2.GetDocumentRequest(document_id=doc_id))
    if not verify_res.found:
        print("4. Final Verification: Document deleted successfully (OK)")
        return True
    else:
        print("4. ❌ Document still exists after deletion!")
        return False


def test_check_plagiarism():
    """Test 4: Plagiarism checking logic."""
    print("\n" + "=" * 50)
    print("TEST 4: Check Plagiarism")
    print("=" * 50)

    stub = get_stub()
    text_to_check = "Nội dung tài liệu batch số 1 dùng để kiểm tra tính năng streaming."
    
    try:
        response = stub.CheckPlagiarism(plagiarism_pb2.CheckRequest(text=text_to_check))
        print(f"Plagiarism: {response.plagiarism_percentage:.1f}%")
        print(f"Severity: {response.severity}")
        print(f"Explanation: {response.explanation[:100]}...")
        
        if response.matches:
            print(f"Matches: {len(response.matches)}")
            for m in response.matches[:1]:
                print(f"  - Top Match: {m.document_title} ({m.similarity_score:.2f})")
        return True
    except Exception as e:
        print(f"❌ Plagiarism Check failed: {e}")
        return False


def test_pdf_indexing():
    """Test 5: Index PDF from MinIO (based on your screenshot)."""
    print("\n" + "=" * 50)
    print("TEST 5: Index PDF from MinIO")
    print("=" * 50)

    stub = get_stub()
    # Using the filename seen in your MinIO screenshot
    pdf_filename = "MachineLearning.pdf" 
    bucket = "plagiarism-docs"

    try:
        print(f"Attempting to index: {bucket}/{pdf_filename}")
        response = stub.IndexPdfFromMinio(plagiarism_pb2.IndexDocumentFromMinioRequest(
            bucket_name=bucket,
            object_path=pdf_filename,
            title="AI PDF Test Index"
        ))
        
        if response.success:
            print(f"✅ Successfully indexed PDF")
            print(f"   Doc ID: {response.document_id}")
            print(f"   Chunks count: {len(response.chunks)}")
            return True
        else:
            print(f"⚠️ Indexing failed (Expected if file not actually in bucket): {response.message}")
            return False
    except Exception as e:
        print(f"❌ PDF Indexing RPC failed: {e}")
        return False


def main():
    """Run all tests in sequence."""
    print("\n🚀 STARTING COMPREHENSIVE SERVICE TESTS\n")
    
    # Track results
    results = []
    
    # Execute tests
    tests = [
        ("Health Check", test_health_check),
        ("Batch Upload", test_batch_upload),
        ("Lifecycle (Get/Delete)", test_document_lifecycle),
        ("Plagiarism Check", test_check_plagiarism),
        ("PDF Indexing", test_pdf_indexing),
    ]
    
    for name, func in tests:
        success = func()
        results.append((name, success))
        time.sleep(1) # Small delay for ES refresh
        
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    all_passed = True
    for name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{name:<25}: {status}")
        if not success and name != "PDF Indexing": # PDF might fail if user haven't uploaded file yet
             all_passed = False
             
    print("\n" + ("🎉 ALL CORE TESTS PASSED" if all_passed else "⚠️ SOME TESTS FAILED"))
    print("=" * 50 + "\n")


if __name__ == "__main__":
    main()


# if __name__ == "__main__":
#     main()
