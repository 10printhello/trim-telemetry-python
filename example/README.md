# Django Example Project

This is a simple Django project with 26 unit tests designed for testing the trim-telemetry-python package.

## Features

- Django REST Framework API
- PostgreSQL database
- Docker Compose setup
- 26 comprehensive unit tests
- E-commerce-like models (Categories, Products, Orders, OrderItems)

## Quick Start

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

5. Test the API:
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

The project includes 20 unit tests covering:
- Model creation and validation
- Model properties and methods
- API endpoints (CRUD operations)
- Custom API actions
- Error handling

Run tests with:
```bash
docker-compose exec web python manage.py test
```

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
