import grpc
import pytest
from src import plagiarism_pb2 # Lưu ý đường dẫn bạn đã generate
from src import plagiarism_pb2_grpc

def test_health_check():
    """Kiểm tra xem Server có đang sống và phản hồi không"""
    # 1. Tạo channel kết nối
    channel = grpc.insecure_channel('localhost:50051')
    stub = plagiarism_pb2_grpc.PlagiarismServiceStub(channel)
    
    # 2. Gửi request
    try:
        response = stub.HealthCheck(plagiarism_pb2.HealthCheckRequest())
        # 3. Kiểm tra kết quả
        assert response.healthy is True
        print("\n gRPC Connection Test: PASSED")
    except grpc.RpcError as e:
        pytest.fail(f" gRPC Connection Test: FAILED - {e.details()}")
    finally:
        channel.close()