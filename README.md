# Trim Telemetry

Rich test telemetry collection package for Trim. Provides detailed instrumentation for Django, pytest, and unittest test frameworks.

## Installation

```bash
pip install trim-telemetry
```

## Usage

### Django Tests

```bash
# Basic usage
python -m trim_telemetry.django_instrumentation manage.py test

# With custom settings
python -m trim_telemetry.django_instrumentation --settings=myapp.settings_test manage.py test

# With specific test arguments
python -m trim_telemetry.django_instrumentation manage.py test myapp.tests

# With Docker
ENVIRONMENT=testing python -m trim_telemetry.django_instrumentation manage.py test
```

### Pytest Tests

```bash
# Basic usage
python -m trim_telemetry.pytest_instrumentation

# With specific test files
python -m trim_telemetry.pytest_instrumentation tests/test_models.py

# With test discovery
python -m trim_telemetry.pytest_instrumentation tests/

# With pytest options
python -m trim_telemetry.pytest_instrumentation -v --tb=short
```

### Unittest Tests

```bash
# Basic usage (auto-discovers tests)
python -m trim_telemetry.unittest_instrumentation

# With specific test modules
python -m trim_telemetry.unittest_instrumentation test_models test_views

# With specific test classes
python -m trim_telemetry.unittest_instrumentation test_models.TestUserModel
```

### With Trim CLI

```bash
# Install the package in your Python environment
pip install trim-telemetry

# Django
make collect TEST_COMMAND="python -m trim_telemetry.django_instrumentation manage.py test"

# Pytest
make collect TEST_COMMAND="python -m trim_telemetry.pytest_instrumentation tests/"

# Unittest
make collect TEST_COMMAND="python -m trim_telemetry.unittest_instrumentation"

# Docker Django
make collect TEST_COMMAND="ENVIRONMENT=testing python -m trim_telemetry.django_instrumentation manage.py test"
```

## Features

- **Rich Telemetry**: Database queries, HTTP calls, performance metrics
- **Network Call Blocking**: Prevents tests from making external HTTP calls
- **Real-time Output**: Streams telemetry data as tests run
- **Docker Compatible**: Works inside Docker containers
- **Framework Support**: Django, pytest, unittest

## Telemetry Data

The package outputs structured telemetry data:

```json
{
  "id": "test_user_creation",
  "name": "test_user_creation", 
  "class": "UserTestCase",
  "module": "users.tests",
  "status": "passed",
  "duration": 1250.5,
  "database_queries": {
    "count": 3,
    "total_duration": 45.2,
    "slow_queries": []
  },
  "http_calls": {
    "count": 0,
    "external_calls": []
  },
  "performance": {
    "is_slow": false,
    "is_db_heavy": false,
    "flags": []
  }
}
```

## Development

```bash
# Install in development mode
pip install -e .

# Run tests
pytest

# Format code
black trim_telemetry/
```
