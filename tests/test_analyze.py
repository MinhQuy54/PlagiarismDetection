import asyncio
from src.core.analyzer import get_analyze

def test_ai_logic():
    analyzer = get_analyze()
    
    # Giả lập dữ liệu
    input_text = "Học máy là một lĩnh vực của trí tuệ nhân tạo tập trung vào việc xây dựng các hệ thống có khả năng học hỏi từ dữ liệu."
    
    matches = [
        {
            "source": "Wikipedia",
            "similarity": 0.92,
            "matched_text": "Học máy (Machine Learning) là một nhánh của AI cho phép máy tính tự học từ dữ liệu để cải thiện hiệu suất."
        }
    ]
    
    print("🧠 Đang nhờ AI phân tích...")
    result = analyzer.analyze(input_text, matches, base_percentage=92.0)
    
    print("-" * 30)
    print(f"📊 Kết quả: {result.plagiarism_percentage}%")
    print(f"⚠️ Mức độ: {result.severity}")
    print(f"📝 Giải thích: {result.explanation}")
    print(f"🎯 Độ tin cậy: {result.confidence}")
    
    if result.suspicious_segments:
        print("🚩 Các đoạn nghi ngờ:")
        for seg in result.suspicious_segments:
            print(f"   - {seg['text']} (Lý do: {seg['reason']})")

if __name__ == "__main__":
    test_ai_logic()