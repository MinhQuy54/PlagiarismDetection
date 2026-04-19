"""Pytest configuration and fixtures."""

import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_text():
    """Sample text for testing."""
    return """
    Đây là một đoạn văn bản mẫu để kiểm tra hệ thống phát hiện đạo văn.
    Hệ thống sử dụng Elasticsearch để lưu trữ và tìm kiếm vector.
    Ollama được sử dụng để tạo embedding và phân tích AI.
    Mỗi đoạn văn được chia thành các chunks nhỏ hơn để so sánh.
    """


@pytest.fixture
def sample_document():
    """Sample document for testing."""
    return {
        "title": "Test Document",
        "content": "This is a test document content for plagiarism detection.",
        "metadata": {"author": "Test Author", "year": "2024"},
        "language": "en",
    }


@pytest.fixture
def mock_embedding():
    """Mock embedding vector."""
    return [0.1] * 768  # 768-dimensional vector
