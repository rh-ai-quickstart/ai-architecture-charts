#!/bin/bash

# Build and publish SQLcl MCP Server to Quay.io

set -e

# Configuration
IMAGE_NAME="oracle-sqlcl-mcp-server"
TAG="1.0.0"
QUAY_REPO="quay.io/ecosystem-appeng"

echo "Building SQLcl MCP Server with verbose logging..."

# Build the container image for x86_64 architecture
docker build --platform linux/amd64 -f Containerfile -t ${IMAGE_NAME}:${TAG} .

# Tag for Quay.io
docker tag ${IMAGE_NAME}:${TAG} ${QUAY_REPO}/${IMAGE_NAME}:${TAG}

echo "Build complete!"
echo "To publish to Quay.io, run:"
echo "  docker push ${QUAY_REPO}/${IMAGE_NAME}:${TAG}"