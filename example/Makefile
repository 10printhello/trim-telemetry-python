# Django Example Project with Telemetry Collection
# Makefile for common development tasks

.PHONY: help build up down logs shell test test-telemetry generate clean migrate superuser

# Default target
help: ## Show this help message
	@echo "Django Example Project with Telemetry Collection"
	@echo "================================================"
	@echo ""
	@echo "Available targets:"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Docker operations
build: ## Build Docker containers
	docker-compose build

up: ## Start the project (build if needed)
	docker-compose up --build -d

down: ## Stop and remove containers
	docker-compose down

logs: ## Show container logs
	docker-compose logs -f

shell: ## Open a shell in the web container
	docker-compose exec web bash

# Database operations
migrate: ## Run Django migrations
	docker-compose exec web python manage.py migrate

superuser: ## Create a Django superuser
	docker-compose exec web python manage.py createsuperuser

# Testing
test: ## Run Django tests (standard)
	docker-compose exec web python manage.py test --verbosity=2

test-telemetry: ## Run tests with telemetry collection
	docker-compose exec web python manage.py test --testrunner=trim_telemetry.django.TelemetryTestRunner --verbosity=2

test-keepdb: ## Run tests with keepdb for faster runs
	docker-compose exec web python manage.py test --testrunner=trim_telemetry.django.TelemetryTestRunner --keepdb --verbosity=2

# Telemetry generation
generate: ## Generate telemetry data (alias for test-telemetry)
	@echo "Generating telemetry data..."
	@echo "Running tests with telemetry collection..."
	docker-compose exec web python manage.py test --testrunner=trim_telemetry.django.TelemetryTestRunner --verbosity=2
	@echo ""
	@echo "Telemetry data generated in .telemetry/ folder"
	@echo "Files created:"
	docker-compose exec web ls -la .telemetry/ || echo "No telemetry files found"


# Data management
clean: ## Clean up containers, volumes, and telemetry data
	docker-compose down -v
	docker-compose exec web rm -rf .telemetry/ || true
	@echo "Cleaned up containers, volumes, and telemetry data"

clean-telemetry: ## Clean only telemetry data
	docker-compose exec web rm -rf .telemetry/ || true
	@echo "Cleaned up telemetry data"

# Development workflow
dev-setup: build up migrate ## Complete development setup
	@echo "Development environment ready!"
	@echo "Run 'make generate' to create telemetry data"
	@echo "Run 'make test' to run the test suite"

# Telemetry analysis
telemetry-latest: ## Show the latest telemetry file
	@echo "Latest telemetry file:"
	docker-compose exec web ls -t .telemetry/ | head -1 | awk '{print $$NF}' | xargs -I {} docker-compose exec web head -1 .telemetry/{} | python3 -m json.tool

telemetry-count: ## Count telemetry records
	@echo "Telemetry records count:"
	docker-compose exec web find .telemetry/ -name "*.ndjson" -exec wc -l {} + | tail -1

# Quick start
quick-start: dev-setup generate ## Complete quick start workflow
	@echo ""
	@echo "🎉 Quick start complete!"
	@echo "✅ Project built and started"
	@echo "✅ Database migrated"
	@echo "✅ Telemetry data generated"
	@echo "✅ API tested"
	@echo ""
	@echo "Next steps:"
	@echo "  - Check telemetry data: make telemetry-latest"
	@echo "  - View logs: make logs"
	@echo "  - Open shell: make shell"
