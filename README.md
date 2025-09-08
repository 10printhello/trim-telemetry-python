# Trim Telemetry

Rich test telemetry collection package for Trim. Provides comprehensive instrumentation for Django, pytest, and unittest test frameworks with detailed performance analysis, database query monitoring, coverage tracking, and network call blocking.

## Installation

```bash
pip install trim-telemetry
```

### Optional Dependencies

For enhanced features, install these optional packages:

```bash
# For code coverage collection
pip install coverage

# For Django template coverage (if using django_coverage_plugin)
pip install django_coverage_plugin
```

### Requirements

- Python 3.8+
- Django 3.2+ (for Django integration)
- pytest 6.0+ (for pytest integration)

## Usage

### Django Tests

#### **Using the Custom Test Runner (Recommended)**

```bash
# Basic usage with custom test runner
python manage.py test --testrunner=trim_telemetry.django_runner.TrimTelemetryRunner

# With specific test modules
python manage.py test --testrunner=trim_telemetry.django_runner.TrimTelemetryRunner core.tests.test_models

# With keepdb for faster runs
python manage.py test --testrunner=trim_telemetry.django_runner.TrimTelemetryRunner --keepdb

# With Docker
ENVIRONMENT=testing python manage.py test --testrunner=trim_telemetry.django_runner.TrimTelemetryRunner
```

#### **Using the Legacy Instrumentation Module**

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

#### **Coverage Collection (Optional)**

To enable code coverage collection, install the coverage package:

```bash
pip install coverage
```

Coverage data will be automatically collected and included in the telemetry output.

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

# Django with custom test runner (recommended)
make collect TEST_COMMAND="python manage.py test --testrunner=trim_telemetry.django_runner.TrimTelemetryRunner"

# Django with legacy instrumentation
make collect TEST_COMMAND="python -m trim_telemetry.django_instrumentation manage.py test"

# Pytest
make collect TEST_COMMAND="python -m trim_telemetry.pytest_instrumentation tests/"

# Unittest
make collect TEST_COMMAND="python -m trim_telemetry.unittest_instrumentation"

# Docker Django with custom test runner
make collect TEST_COMMAND="ENVIRONMENT=testing python manage.py test --testrunner=trim_telemetry.django_runner.TrimTelemetryRunner"

# Docker Django with legacy instrumentation
make collect TEST_COMMAND="ENVIRONMENT=testing python -m trim_telemetry.django_instrumentation manage.py test"
```

## Features

### 🎯 **Rich Telemetry Collection**
- **Database Query Analysis**: Per-test query isolation, slow query detection, duplicate query identification
- **Performance Metrics**: Accurate P95/P99 percentiles, median, average durations with statistical analysis
- **Code Coverage**: Real-time coverage collection with file-level breakdown and missing line identification
- **Network Call Blocking**: Prevents tests from making external HTTP calls with detailed blocking reports

### 🔧 **Advanced Analytics**
- **Query Type Breakdown**: SELECT, INSERT, UPDATE, DELETE query categorization
- **Performance Flags**: Intelligent flagging of slow tests, DB-heavy tests, N+1 query patterns
- **Statistical Analysis**: Proper percentile calculations across test suite execution
- **Test Isolation**: Accurate per-test metrics without cross-test contamination

### 🚀 **Framework Support**
- **Django**: Custom test runner with full Django integration
- **Pytest**: Comprehensive pytest plugin with rich instrumentation
- **Unittest**: Enhanced unittest runner with telemetry collection
- **Docker Compatible**: Works seamlessly inside Docker containers

## Telemetry Data

The package outputs comprehensive structured telemetry data for each test:

### 📊 **Complete Telemetry Structure**

```json
{
  "id": "test_user_creation",
  "name": "test_user_creation",
  "class": "UserTestCase", 
  "module": "users.tests",
  "file": "users/tests.py",
  "line": 0,
  "status": "passed",
  "duration": 1250,
  "start_time": "2025-09-08T13:30:15.123456",
  "end_time": "2025-09-08T13:30:16.373456",
  "tags": [],
  "fixtures": [],
  
  "database_queries": {
    "count": 15,
    "total_duration": 245.67,
    "slow_queries": [
      {
        "sql": "SELECT * FROM users WHERE email = 'test@example.com'",
        "time": 0.156,
        "duration": 156
      }
    ],
    "duplicate_queries": [
      {
        "sql": "SELECT id FROM posts WHERE user_id = %s",
        "count": 3
      }
    ],
    "query_types": {
      "SELECT": 12,
      "INSERT": 2, 
      "UPDATE": 1,
      "DELETE": 0,
      "OTHER": 0
    },
    "avg_duration": 16.38,
    "max_duration": 156.0
  },
  
  "http_calls": {
    "count": 0,
    "total_duration": 0,
    "external_calls": [],
    "blocked_calls": []
  },
  
  "performance": {
    "is_slow": false,
    "is_db_heavy": false,
    "is_network_heavy": false,
    "has_blocked_network_calls": false,
    "current_duration": 1250,
    "avg_duration": 180,
    "median_duration": 175,
    "p95_duration": 420,
    "p99_duration": 580,
    "total_tests_run": 15,
    "flags": ["moderate_db_queries"]
  },
  
  "coverage": {
    "lines_covered": 1250,
    "lines_total": 1500,
    "coverage_percent": 83.33,
    "files": [
      {
        "file": "/path/to/models.py",
        "lines_covered": 45,
        "lines_total": 50,
        "coverage_percent": 90.0,
        "missing_lines": [23, 45, 67]
      }
    ],
    "status": "collected"
  },
  
  "logs": [],
  "metadata": {}
}
```

### 🎯 **Key Telemetry Features**

#### **Database Query Analysis**
- **Per-test isolation**: Each test shows only its own queries
- **Slow query detection**: Queries > 100ms with full SQL details
- **Duplicate detection**: Identifies repeated SQL statements
- **Query categorization**: Breakdown by SELECT/INSERT/UPDATE/DELETE
- **Performance metrics**: Average and maximum query durations

#### **Performance Analytics**
- **Statistical percentiles**: Accurate P95/P99 calculations across test suite
- **Performance flags**: Intelligent detection of slow, DB-heavy, or problematic tests
- **N+1 detection**: Identifies potential N+1 query patterns
- **Duration tracking**: Current, average, median, and percentile durations

#### **Code Coverage**
- **Real-time collection**: Live coverage tracking during test execution
- **File-level breakdown**: Coverage per file with missing line numbers
- **Percentage accuracy**: Precise coverage calculations
- **Status tracking**: Indicates coverage collection success/failure

#### **Network Call Blocking**
- **External call prevention**: Blocks HTTP requests to prevent test flakiness
- **Detailed reporting**: Shows which calls were blocked and where
- **Thread-safe**: Works across multiple test threads

## Output Format

The telemetry data is output in real-time as tests execute. Each test produces a JSON line prefixed with `TEST_RESULT:`:

```
TEST_RESULT:{"id": "test_user_creation", "name": "test_user_creation", ...}
TEST_RESULT:{"id": "test_user_deletion", "name": "test_user_deletion", ...}
TEST_SUMMARY:{"total_tests": 25, "passed_tests": 23, "failed_tests": 2, "skipped_tests": 0, "exit_code": 1}
```

### 📈 **Interpreting Performance Metrics**

#### **Duration Percentiles**
- **P95**: 95% of tests run faster than this duration
- **P99**: 99% of tests run faster than this duration  
- **Median**: 50% of tests run faster than this duration
- **Average**: Mean duration across all tests

#### **Performance Flags**
- `very_slow`: Test duration > 5 seconds
- `slow`: Test duration > 1 second
- `high_db_queries`: > 100 database queries
- `moderate_db_queries`: > 50 database queries
- `potential_n_plus_1_queries`: > 10 SELECT queries (possible N+1 pattern)
- `network_calls_blocked`: Test attempted external HTTP calls

#### **Database Query Analysis**
- **Slow queries**: Queries taking > 100ms with full SQL
- **Duplicate queries**: Repeated SQL statements within the test
- **Query types**: Breakdown by SELECT/INSERT/UPDATE/DELETE operations

## Development

```bash
# Install in development mode
pip install -e .

# Run tests
pytest

# Format code
black trim_telemetry/
```
