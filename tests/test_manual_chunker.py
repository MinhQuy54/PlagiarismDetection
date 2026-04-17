import logging
from src.core.chunker import get_chunker

# Cấu hình logging để xem quá trình xử lý
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def run_manual_test():
    chunker = get_chunker()
    
    # Giả lập cấu hình nhỏ để dễ quan sát logic băm
    chunker.chunk_size = 15      # 15 từ mỗi chunk
    chunker.chunk_overlap = 5    # Gối đầu 5 từ
    chunker.min_chunk_size = 5   # Không lấy đoạn cuối nếu dưới 5 từ
    
    print("="*50)
    print("🚀 BẮT ĐẦU KIỂM TRA BỘ BĂM VĂN BẢN (MANUAL TEST)")
    print("="*50)

    # 1. Test với văn bản tiếng Việt thực tế
    raw_text = """
    Trí tuệ nhân tạo (AI) là một ngành thuộc lĩnh vực khoa học máy tính. 
    Nó tập trung vào việc tạo ra những cỗ máy thông minh có khả năng thực hiện 
    các công việc vốn đòi hỏi trí thông minh của con người. 
    Trong đồ án này, chúng ta sử dụng Ollama và Elasticsearch để phát hiện đạo văn 
    một cách hiệu quả và chính xác nhất trên môi trường local.
    """
    
    print(f"\n📝 Văn bản gốc ({chunker.get_word_count(raw_text)} từ):")
    print(f"'{raw_text.strip()[:100]}...'")
    
    # Chạy băm
    chunks = chunker.chunk_text(raw_text)
    
    print(f"\n📊 Kết quả: Chia thành {len(chunks)} đoạn.")
    
    for i, chunk in enumerate(chunks):
        print(f"\n--- 📦 ĐOẠN {i} ({chunk.word_count} từ) ---")
        print(f"Nội dung: {chunk.text}")
        print(f"Vị trí: char {chunk.start_char} -> {chunk.end_char}")
        
        # Kiểm tra tính gối đầu với đoạn sau
        if i < len(chunks) - 1:
            next_chunk = chunks[i+1]
            # Lấy 5 từ cuối của chunk hiện tại
            overlap_tail = " ".join(chunk.text.split()[-chunker.chunk_overlap:])
            # Lấy 5 từ đầu của chunk kế tiếp
            overlap_head = " ".join(next_chunk.text.split()[:chunker.chunk_overlap])
            
            print(f"🔗 Kiểm tra gối đầu (Overlap):")
            print(f"   Tail C{i}:   '{overlap_tail}'")
            print(f"   Head C{i+1}: '{overlap_head}'")
            
            if overlap_tail == overlap_head:
                print("   ✅ KHỚP!")
            else:
                print("   ❌ KHÔNG KHỚP - Cần kiểm tra lại logic index!")

    # 2. Test nhận diện ngôn ngữ
    print("\n" + "="*50)
    print("🌍 KIỂM TRA NHẬN DIỆN NGÔN NGỮ")
    texts = {
        "vi": "Đây là một đoạn văn bản mẫu bằng tiếng Việt.",
        "en": "This is a sample text written in English for testing purposes.",
        "short": "Hi there!"
    }
    
    for code, text in texts.items():
        lang = chunker.detect_language(text)
        print(f"👉 Input: '{text}' -> Detected: [{lang}]")

if __name__ == "__main__":
    run_manual_test()