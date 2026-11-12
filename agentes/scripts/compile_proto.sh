#!/bin/bash

# Script para compilar proto files para Python y Go

echo "Compilando proto files..."

# Compilar para Python
echo "1. Compilando para Python..."
python -m grpc_tools.protoc \
  -I./proto \
  --python_out=. \
  --grpc_python_out=. \
  proto/services.proto

if [ $? -eq 0 ]; then
    echo "✓ Python proto files compilados"
else
    echo "✗ Error compilando Python proto files"
    exit 1
fi

# Compilar para Go
echo "2. Compilando para Go..."
protoc \
  --go_out=. \
  --go_opt=paths=source_relative \
  --go-grpc_out=. \
  --go-grpc_opt=paths=source_relative \
  proto/services.proto

if [ $? -eq 0 ]; then
    echo "✓ Go proto files compilados"
else
    echo "✗ Error compilando Go proto files"
    exit 1
fi

echo ""
echo "✓ Compilación completa"
echo ""
echo "Archivos generados:"
echo "  - services_pb2.py"
echo "  - services_pb2_grpc.py"
echo "  - proto/services.pb.go"
echo "  - proto/services_grpc.pb.go"
