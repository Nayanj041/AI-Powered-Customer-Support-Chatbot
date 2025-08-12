#!/bin/bash

# Development setup script for AI-Powered Customer Support Chatbot

set -e  # Exit on error

echo "🤖 Setting up AI-Powered Customer Support Chatbot development environment..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Python version: $PYTHON_VERSION"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p models/cache
mkdir -p logs
mkdir -p static

# Copy environment file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "⚙️ Creating environment file..."
    cp .env.example .env
    echo "📝 Please edit .env file with your configuration"
fi

# Check if Docker is available for services
if command -v docker &> /dev/null && command -v docker-compose &> /dev/null; then
    echo "🐳 Docker found. You can run 'docker-compose up -d' to start MongoDB and Redis"
else
    echo "⚠️ Docker not found. Please install MongoDB and Redis manually or install Docker"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "To start the development server:"
echo "  1. Activate virtual environment: source venv/bin/activate"
echo "  2. Start services: docker-compose up -d (if using Docker)"
echo "  3. Configure .env file with your settings"
echo "  4. Run the application: uvicorn app.main:app --reload"
echo ""
echo "The application will be available at: http://localhost:8000"
echo "API documentation: http://localhost:8000/docs"
echo "Chat interface: http://localhost:8000/chat"
