#!/bin/bash

# Deployment script for AI-Powered Customer Support Chatbot

set -e

echo "🚀 Deploying AI-Powered Customer Support Chatbot..."

# Default values
ENVIRONMENT=${1:-production}
DOCKER_IMAGE_TAG=${2:-latest}

echo "Environment: $ENVIRONMENT"
echo "Docker image tag: $DOCKER_IMAGE_TAG"

# Build Docker image
echo "🏗️ Building Docker image..."
docker build -t chatbot:$DOCKER_IMAGE_TAG .

# Tag for registry (customize as needed)
# docker tag chatbot:$DOCKER_IMAGE_TAG your-registry/chatbot:$DOCKER_IMAGE_TAG

# Push to registry (uncomment if using registry)
# echo "📤 Pushing to registry..."
# docker push your-registry/chatbot:$DOCKER_IMAGE_TAG

# Deploy based on environment
case $ENVIRONMENT in
    "development"|"dev")
        echo "🔧 Deploying to development environment..."
        docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
        ;;
    "staging"|"stage")
        echo "🎭 Deploying to staging environment..."
        docker-compose -f docker-compose.yml -f docker-compose.staging.yml up -d
        ;;
    "production"|"prod")
        echo "🏭 Deploying to production environment..."
        docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
        ;;
    *)
        echo "❌ Unknown environment: $ENVIRONMENT"
        echo "Available environments: development, staging, production"
        exit 1
        ;;
esac

echo ""
echo "✅ Deployment completed!"
echo "🌐 Application should be available at: http://localhost:8000"
echo "📊 Health check: http://localhost:8000/api/health"

# Wait a moment and perform health check
echo "⏳ Waiting for services to start..."
sleep 10

if curl -f http://localhost:8000/api/health > /dev/null 2>&1; then
    echo "✅ Health check passed!"
else
    echo "⚠️ Health check failed. Please check the logs:"
    echo "docker-compose logs chatbot"
fi
