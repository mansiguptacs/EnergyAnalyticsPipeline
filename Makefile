# ==============================================================================
# Energy Analytics Pipeline — Makefile
# ==============================================================================
# Usage:
#   make up              Start all services
#   make down            Stop all services
#   make init-db         Initialize database schemas
#   make generate-data   Generate sample data
#   make run-pipeline    Run the ingestion pipeline locally
#   make test            Run tests
#   make lint            Run linters
#   make clean           Remove containers, volumes, and cached files
# ==============================================================================

.PHONY: help up down init-db generate-data run-pipeline test lint clean logs shell-db

# Default target
help: ## Show this help message
	@echo "Energy Analytics Pipeline — Available commands:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ==============================================================================
# Docker Compose
# ==============================================================================

up: ## Start all services (PostgreSQL, Airflow, Superset, Grafana)
	docker compose up -d
	@echo ""
	@echo "✅ Services starting..."
	@echo "   Airflow UI:   http://localhost:8080  (admin/admin)"
	@echo "   PostgreSQL:   localhost:5432         (energy_user/energy_pass)"
	@echo "   Grafana:      http://localhost:3000  (admin/admin)"
	@echo ""

down: ## Stop all services
	docker compose down

down-clean: ## Stop all services and remove volumes (DESTRUCTIVE)
	docker compose down -v

logs: ## Tail logs from all services
	docker compose logs -f

logs-airflow: ## Tail Airflow scheduler logs
	docker compose logs -f airflow-scheduler

# ==============================================================================
# Database
# ==============================================================================

init-db: ## Initialize database schemas and seed dimensions
	@echo "🔧 Initializing database schemas..."
	docker compose exec energy-postgres psql -U energy_user -d energy_db \
		-f /docker-entrypoint-initdb.d/001_create_schemas.sql
	docker compose exec energy-postgres psql -U energy_user -d energy_db \
		-f /docker-entrypoint-initdb.d/002_create_raw_tables.sql
	docker compose exec energy-postgres psql -U energy_user -d energy_db \
		-f /docker-entrypoint-initdb.d/003_create_staging_tables.sql
	docker compose exec energy-postgres psql -U energy_user -d energy_db \
		-f /docker-entrypoint-initdb.d/004_create_analytics_tables.sql
	docker compose exec energy-postgres psql -U energy_user -d energy_db \
		-f /docker-entrypoint-initdb.d/005_create_dq_tables.sql
	docker compose exec energy-postgres psql -U energy_user -d energy_db \
		-f /docker-entrypoint-initdb.d/006_create_indexes.sql
	docker compose exec energy-postgres psql -U energy_user -d energy_db \
		-f /docker-entrypoint-initdb.d/007_seed_dimensions.sql
	@echo "✅ Database initialized successfully!"

shell-db: ## Open a psql shell to the energy database
	docker compose exec energy-postgres psql -U energy_user -d energy_db

# ==============================================================================
# Data
# ==============================================================================

generate-data: ## Generate sample data for development
	@echo "📊 Generating sample data..."
	docker compose exec airflow-scheduler python /opt/airflow/scripts/generate_sample_data.py
	@echo "✅ Sample data generated in data/sample/"

run-pipeline: ## Run the ingestion pipeline (loads sample data into raw layer)
	@echo "🚀 Running ingestion pipeline..."
	docker compose exec airflow-scheduler python -m src.ingestion.meter_readings_ingest \
		--source-dir /opt/airflow/data/sample \
		--db-conn "postgresql://energy_user:energy_pass@energy-postgres:5432/energy_db"
	@echo "✅ Pipeline complete!"

# ==============================================================================
# Development
# ==============================================================================

test: ## Run all tests
	pytest tests/ -v --cov=src --cov-report=term-missing

test-unit: ## Run unit tests only
	pytest tests/unit/ -v -m unit

test-integration: ## Run integration tests only (requires database)
	pytest tests/integration/ -v -m integration

lint: ## Run linters (ruff + black check)
	ruff check src/ dags/ tests/ scripts/
	black --check src/ dags/ tests/ scripts/

format: ## Auto-format code
	ruff check --fix src/ dags/ tests/ scripts/
	black src/ dags/ tests/ scripts/

typecheck: ## Run mypy type checking
	mypy src/ --ignore-missing-imports

# ==============================================================================
# Cleanup
# ==============================================================================

clean: ## Remove containers, volumes, and Python cache
	docker compose down -v 2>/dev/null || true
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf htmlcov/ .coverage coverage.xml
	@echo "✅ Cleaned up!"
