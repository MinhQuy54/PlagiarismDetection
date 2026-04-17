

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"&& pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"

PROTO_DIR="$PROJECT_ROOT/proto"
OUTPUT_DIR="$PROJECT_ROOT/src"
echo "Generating gRPC code..."
echo "Proto directory: $PROTO_DIR"
echo "Output directory: $OUTPUT_DIR"

# Generate Python code

python -m grpc_tools.protoc \
    -I"$PROTO_DIR" \
    --python_out="$OUTPUT_DIR" \
    --pyi_out="$OUTPUT_DIR" \
    --grpc_python_out="$OUTPUT_DIR" \
    "$PROTO_DIR/plagiarism.proto"


if [ $? -eq 0 ]; then
    echo "Successfully generated:"
    echo "  - $OUTPUT_DIR/plagiarism_pb2.py"
    echo "  - $OUTPUT_DIR/plagiarism_pb2.pyi"
    echo "  - $OUTPUT_DIR/plagiarism_pb2_grpc.py"

    # Fix import paths (Python 3 style)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' 's/import plagiarism_pb2/from src import plagiarism_pb2/g' "$OUTPUT_DIR/plagiarism_pb2_grpc.py"
    else
        # Linux
        sed -i 's/import plagiarism_pb2/from src import plagiarism_pb2/g' "$OUTPUT_DIR/plagiarism_pb2_grpc.py"
    fi

    echo "Import paths fixed."
else
    echo "Error generating gRPC code!"
    exit 1
fi
