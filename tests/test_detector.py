import pytest
from src.core.detector import get_detector

def test_plagiarism_detection_flow():
    detector = get_detector()
    
    # Giả sử trong kho ES đã có bài về "Học máy"
    # Chúng ta gửi một câu đã bị sửa đổi nhẹ
    query_text = "Machine learning là lĩnh vực của trí tuệ nhân tạo dùng dữ liệu để học."
    
    result = detector.check_plagiarism(query_text)
    
    assert "plagiarism_percentage" in result
    assert isinstance(result["detailed_results"], list)
    
    print(f"\n🔍 Tỷ lệ đạo văn: {result['plagiarism_percentage']}%")
    if result["detailed_results"]:
        print(f"📄 Đoạn trùng khớp nhất: {result['detailed_results'][0]['matches'][0]['content']}")

if __name__ == "__main__":
    test_plagiarism_detection_flow()