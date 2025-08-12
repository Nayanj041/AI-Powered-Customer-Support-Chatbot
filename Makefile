.PHONY: help setup install test lint format clean run docker-build docker-up docker-down

# Default target
help:
	@echo "Available commands:"
	@echo "  setup      - Set up development environment"
	@echo "  install    - Install dependencies"
	@echo "  test       - Run tests"
	@echo "  lint       - Run linting"
	@echo "  format     - Format code"
	@echo "  clean      - Clean temporary files"
	@echo "  run        - Run development server"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-up  - Start Docker services"
	@echo "  docker-down - Stop Docker services"

# Set up development environment
setup:
	@echo "Setting up development environment..."
	@chmod +x scripts/setup.sh
	@./scripts/setup.sh

# Install dependencies
install:
	pip install -r requirements.txt

# Run tests
test:
	@echo "Running tests..."
	@chmod +x scripts/test.sh
	@./scripts/test.sh

# Run linting
lint:
	@echo "Running linting..."
	flake8 app/ tests/ --max-line-length=88 --extend-ignore=E203,W503
	black --check app/ tests/
	isort --check-only app/ tests/

# Format code
format:
	@echo "Formatting code..."
	black app/ tests/
	isort app/ tests/

# Clean temporary files
clean:
	@echo "Cleaning temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/

# Run development server
run:
	@echo "Starting development server..."
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Build Docker image
docker-build:
	@echo "Building Docker image..."
	docker build -t chatbot:latest .

# Start Docker services
docker-up:
	@echo "Starting Docker services..."
	docker-compose up -d

# Stop Docker services  
docker-down:
	@echo "Stopping Docker services..."
	docker-compose down

# Start services with tools (MongoDB Express, Redis Commander)
docker-up-tools:
	@echo "Starting Docker services with management tools..."
	docker-compose --profile tools up -d

# View logs
logs:
	docker-compose logs -f chatbot

# Deploy (production)
deploy:
	@echo "Deploying to production..."
	@chmod +x scripts/deploy.sh
	@./scripts/deploy.sh production

# Deploy (development)
deploy-dev:
	@echo "Deploying to development..."
	@chmod +x scripts/deploy.sh
	@./scripts/deploy.sh development

# Database operations
db-reset:
	@echo "Resetting database..."
	docker-compose exec mongodb mongo customer_support_chatbot --eval "db.dropDatabase()"
	docker-compose exec mongodb mongo customer_support_chatbot < mongo-init.js

# Install pre-commit hooks
install-hooks:
	pre-commit install

# Run pre-commit on all files
pre-commit:
	pre-commit run --all-files

# Health check
health:
	@echo "Checking application health..."
	curl -f http://localhost:8000/api/health || echo "Health check failed"

# Install development dependencies
install-dev:
	pip install -r requirements.txt
	pip install pytest pytest-asyncio pytest-cov black flake8 isort pre-commit

# Generate requirements from current environment
freeze:
	pip freeze > requirements.txt

# Run specific test file
test-file:
	@read -p "Enter test file (e.g., tests/test_api.py): " file; \
	python -m pytest $$file -v

# Interactive Python shell with app context
shell:
	@echo "Starting interactive shell..."
	python -c "from app.main import app; import IPython; IPython.embed()"

# Generate API documentation
docs:
	@echo "API documentation available at http://localhost:8000/docs"
	@echo "Or visit http://localhost:8000/redoc for alternative docs"
