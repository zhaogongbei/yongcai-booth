# D-Booth Project Makefile
# Quick commands for development and deployment

.PHONY: help install dev build test lint clean deploy hygiene

help: ## Show this help message
	@echo "D-Booth Development Commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# Installation
install: ## Install all dependencies (backend + frontend + runtime)
	@echo "Installing Backend dependencies..."
	cd D-Booth/backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt -r requirements-dev.txt
	@echo "Installing Frontend dependencies..."
	cd D-Booth/frontend && npm ci
	@echo "Installing Runtime dependencies..."
	cd D-Booth/runtime-dotnet && dotnet restore

install-backend: ## Install backend dependencies only
	cd D-Booth/backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt -r requirements-dev.txt

install-frontend: ## Install frontend dependencies only
	cd D-Booth/frontend && npm ci

install-runtime: ## Install runtime dependencies only
	cd D-Booth/runtime-dotnet && dotnet restore

# Development
dev: ## Start all development servers
	@echo "Starting development servers..."
	make -j3 dev-backend dev-frontend dev-runtime

dev-backend: ## Start backend development server
	cd D-Booth/backend && source venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## Start frontend development server
	cd D-Booth/frontend && npm run dev

dev-runtime: ## Start runtime development server
	cd D-Booth/runtime-dotnet && dotnet run --project src/Booth.Runtime.ApiHost

# Build
build: ## Build all projects
	make build-backend build-frontend build-runtime

build-backend: ## Build backend
	cd D-Booth/backend && source venv/bin/activate && python -m build

build-frontend: ## Build frontend for production
	cd D-Booth/frontend && npm run build

build-runtime: ## Build runtime
	cd D-Booth/runtime-dotnet && dotnet build -c Release

# Testing
test: ## Run all tests
	make test-backend test-frontend test-runtime

test-backend: ## Run backend tests
	cd D-Booth/backend && source venv/bin/activate && pytest --cov=app --cov-report=html

test-frontend: ## Run frontend tests
	cd D-Booth/frontend && npm run typecheck

test-runtime: ## Run runtime tests
	cd D-Booth/runtime-dotnet && dotnet test

# Code Quality
lint: ## Run linters on all projects
	make lint-backend lint-frontend lint-runtime

lint-backend: ## Lint backend code
	cd D-Booth/backend && source venv/bin/activate && black . && isort . && ruff check app/ --select E9,F63,F7,F82

lint-frontend: ## Lint frontend code
	cd D-Booth/frontend && npm run typecheck

lint-runtime: ## Lint runtime code
	cd D-Booth/runtime-dotnet && dotnet format

format: ## Format all code
	make format-backend format-frontend format-runtime

format-backend: ## Format backend code
	cd D-Booth/backend && source venv/bin/activate && black . && isort .

format-frontend: ## Format frontend code
	@echo "Frontend formatter is not configured yet."

format-runtime: ## Format runtime code
	cd D-Booth/runtime-dotnet && dotnet format

# Database
db-migrate: ## Run database migrations
	cd D-Booth/backend && source venv/bin/activate && alembic upgrade head

db-rollback: ## Rollback last migration
	cd D-Booth/backend && source venv/bin/activate && alembic downgrade -1

db-reset: ## Reset database (WARNING: destroys data)
	cd D-Booth/backend && source venv/bin/activate && alembic downgrade base && alembic upgrade head

db-seed: ## Seed database with test data
	cd D-Booth/backend && source venv/bin/activate && python scripts/seed_db.py

# Docker
docker-up: ## Start all services with Docker Compose
	cd D-Booth/backend && docker-compose up -d

docker-down: ## Stop all Docker services
	cd D-Booth/backend && docker-compose down

docker-build: ## Build Docker images
	cd D-Booth/backend && docker-compose build

docker-logs: ## View Docker logs
	cd D-Booth/backend && docker-compose logs -f

# Deployment
deploy-backend: ## Deploy backend to production
	@echo "Deploying backend..."
	cd D-Booth/backend && ./deploy.sh

deploy-frontend: ## Deploy frontend to production
	@echo "Deploying frontend..."
	cd D-Booth/frontend && npm run build && ./deploy.sh

# Maintenance
clean: ## Clean build artifacts and caches
	@echo "Cleaning build artifacts..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "node_modules" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "dist" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "build" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "bin" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "obj" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true

hygiene: ## Check tracked generated artifacts and local-only files
	python tools/check_repository_hygiene.py

logs: ## View application logs
	tail -f D-Booth/backend/logs/*.log

# Version Management
version: ## Show current version
	@cat VERSION

version-patch: ## Bump patch version (x.y.Z)
	@current=$$(cat VERSION); \
	major=$$(echo $$current | cut -d. -f1); \
	minor=$$(echo $$current | cut -d. -f2); \
	patch=$$(echo $$current | cut -d. -f3); \
	new_patch=$$((patch + 1)); \
	echo "$$major.$$minor.$$new_patch" > VERSION; \
	echo "Version bumped to $$major.$$minor.$$new_patch"

version-minor: ## Bump minor version (x.Y.0)
	@current=$$(cat VERSION); \
	major=$$(echo $$current | cut -d. -f1); \
	minor=$$(echo $$current | cut -d. -f2); \
	new_minor=$$((minor + 1)); \
	echo "$$major.$$new_minor.0" > VERSION; \
	echo "Version bumped to $$major.$$new_minor.0"

version-major: ## Bump major version (X.0.0)
	@current=$$(cat VERSION); \
	major=$$(echo $$current | cut -d. -f1); \
	new_major=$$((major + 1)); \
	echo "$$new_major.0.0" > VERSION; \
	echo "Version bumped to $$new_major.0.0"

# Git
commit: ## Commit changes with conventional commit message
	@read -p "Type (feat/fix/refactor/docs/test/chore): " type; \
	read -p "Scope (backend/frontend/runtime): " scope; \
	read -p "Message: " msg; \
	git add -A; \
	git commit -m "$$type($$scope): $$msg"

push: ## Push to remote repository
	git push origin $$(git branch --show-current)

# Health Check
health: ## Check all services health
	@echo "Checking Backend..."
	@curl -s http://localhost:8000/health | jq . || echo "Backend not running"
	@echo "Checking Frontend..."
	@curl -s http://localhost:5173 > /dev/null && echo "Frontend running" || echo "Frontend not running"
	@echo "Checking Runtime..."
	@curl -s http://localhost:5000/v1/health | jq . || echo "Runtime not running"

# Documentation
docs: ## Generate documentation
	cd D-Booth/backend && source venv/bin/activate && pdoc --html --output-dir docs app/
	@echo "Frontend documentation generator is not configured yet."

docs-serve: ## Serve documentation locally
	cd docs && python -m http.server 8080
