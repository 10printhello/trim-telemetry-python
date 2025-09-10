# Django Example Project

This is a simple Django project with 26 unit tests designed for testing the trim-telemetry-python package.

## Features

- Django REST Framework API
- PostgreSQL database
- Docker Compose setup
- 26 comprehensive unit tests
- E-commerce-like models (Categories, Products, Orders, OrderItems)

## Quick Start

### Using Makefile (Recommended)

The project includes a comprehensive Makefile for easy development:

```bash
# Complete setup and generate telemetry data
make quick-start

# Or step by step:
make dev-setup    # Build, start, and migrate
make generate     # Generate telemetry data
make api-test     # Test API endpoints
```

### Manual Setup

1. Build and start the services:
```bash
docker-compose up --build -d
```

2. Wait for the database to initialize (about 10-15 seconds), then run migrations:
```bash
docker-compose exec web python manage.py migrate
```

3. Create a superuser (optional):
```bash
docker-compose exec web python manage.py createsuperuser
```

4. Run tests:
```bash
docker-compose exec web python manage.py test
```

5. Run tests with telemetry collection:
```bash
# Using the trim-telemetry-python test runner
docker-compose exec web python manage.py test --testrunner=trim_telemetry.django.TelemetryTestRunner

# With keepdb for faster runs
docker-compose exec web python manage.py test --testrunner=trim_telemetry.django.TelemetryTestRunner --keepdb
```

6. Test the API:
```bash
# List categories
curl http://localhost:8000/api/categories/

# Create a category
curl -X POST -H "Content-Type: application/json" \
  -d '{"name": "Electronics", "description": "Electronic devices"}' \
  http://localhost:8000/api/categories/
```

## API Endpoints

- `GET /api/categories/` - List all categories
- `POST /api/categories/` - Create a new category
- `GET /api/categories/{id}/` - Get category details
- `GET /api/categories/{id}/products/` - Get products in a category

- `GET /api/products/` - List all products
- `POST /api/products/` - Create a new product
- `GET /api/products/in_stock/` - Get in-stock products
- `GET /api/products/by_category/?category_id={id}` - Get products by category

- `GET /api/orders/` - List all orders
- `POST /api/orders/` - Create a new order
- `POST /api/orders/{id}/cancel/` - Cancel an order
- `POST /api/orders/{id}/ship/` - Ship an order

## Testing

The project includes 26 unit tests covering:
- Model creation and validation
- Model properties and methods
- API endpoints (CRUD operations)
- Custom API actions
- Error handling

### Standard Test Execution

Run tests with:
```bash
docker-compose exec web python manage.py test
```

### Telemetry Collection

This example project includes the [trim-telemetry-python](https://github.com/10printhello/trim-telemetry-python) package for collecting detailed telemetry data during test execution.

Run tests with telemetry collection:
```bash
# Basic telemetry collection
docker-compose exec web python manage.py test --testrunner=trim_telemetry.django.TelemetryTestRunner

# With keepdb for faster runs
docker-compose exec web python manage.py test --testrunner=trim_telemetry.django.TelemetryTestRunner --keepdb

# Run specific test modules with telemetry
docker-compose exec web python manage.py test --testrunner=trim_telemetry.django.TelemetryTestRunner demo_app.tests.CategoryModelTest
```

The telemetry data will be written to a `.telemetry/` folder in the container, containing detailed information about:
- Database query performance and counts
- Test execution duration
- Network calls made during tests
- Test status and results

For more information about the telemetry package, see the [trim-telemetry-python documentation](https://github.com/10printhello/trim-telemetry-python).

## Makefile Targets

The project includes a comprehensive Makefile with the following targets:

### Development
- `make help` - Show all available targets
- `make dev-setup` - Complete development setup (build, start, migrate)
- `make quick-start` - Complete workflow (setup + generate + test)

### Docker Operations
- `make build` - Build Docker containers
- `make up` - Start the project (build if needed)
- `make down` - Stop and remove containers
- `make logs` - Show container logs
- `make shell` - Open a shell in the web container

### Testing & Telemetry
- `make test` - Run standard Django tests
- `make test-telemetry` - Run tests with telemetry collection
- `make test-keepdb` - Run tests with keepdb for faster runs
- `make generate` - Generate telemetry data (alias for test-telemetry)

### API Testing
- `make api-test` - Test API endpoints with sample requests

### Data Management
- `make migrate` - Run Django migrations
- `make superuser` - Create a Django superuser
- `make clean` - Clean up containers, volumes, and telemetry data
- `make clean-telemetry` - Clean only telemetry data

### Telemetry Analysis
- `make telemetry-latest` - Show the latest telemetry file
- `make telemetry-count` - Count telemetry records

## Database

The project uses PostgreSQL with the following default settings:
- Database: example_db
- User: example_user
- Password: example_password
- Host: db (Docker service name)
- Port: 5432

## Environment Variables

You can override default settings using environment variables:
- `DEBUG` - Django debug mode (default: 1)
- `POSTGRES_DB` - Database name (default: example_db)
- `POSTGRES_USER` - Database user (default: example_user)
- `POSTGRES_PASSWORD` - Database password (default: example_password)
- `POSTGRES_HOST` - Database host (default: db)
- `POSTGRES_PORT` - Database port (default: 5432)
