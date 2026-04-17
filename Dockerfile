FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (including OpenCV dependencies)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Generate gRPC code
RUN python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./src \
    --pyi_out=./src \
    --grpc_python_out=./src \
    ./proto/plagiarism.proto \
    && sed -i 's/import plagiarism_pb2/from src import plagiarism_pb2/g' ./src/plagiarism_pb2_grpc.py

# Expose gRPC port
EXPOSE 50051

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import grpc; channel = grpc.insecure_channel('localhost:50051'); grpc.channel_ready_future(channel).result(timeout=5)" || exit 1

# Run server
CMD ["python", "-m", "src.server"]
