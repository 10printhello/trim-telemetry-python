# Test Telemetry

Rich test telemetry collection package for Python test frameworks. Provides comprehensive instrumentation for Django, pytest, and unittest with detailed performance analysis, database query monitoring, and network call detection.

## Installation

```bash
pip install trim-telemetry
```

### Optional Dependencies

No additional dependencies required. The package works out of the box with standard Python test frameworks.

### Requirements

- Python 3.8+
- Django 3.2+ (for Django integration)
- pytest 6.0+ (for pytest integration)

### Documentation

- **[README.md](README.md)**: Installation, usage, and examples
- **[SCHEMA.md](SCHEMA.md)**: Complete schema documentation and field descriptions

## Usage

### Django Tests

```bash
# Method 1: Direct execution (requires Django environment setup)
python -m trim_telemetry.django [test-args]

# Method 2: Via manage.py (recommended for Django projects)
python manage.py test --testrunner=trim_telemetry.django.TelemetryTestRunner

# With specific test modules
python manage.py test --testrunner=trim_telemetry.django.TelemetryTestRunner core.tests.test_models

# With keepdb for faster runs
python manage.py test --testrunner=trim_telemetry.django.TelemetryTestRunner --keepdb

# With Docker
ENVIRONMENT=testing python manage.py test --testrunner=trim_telemetry.django.TelemetryTestRunner
```

### Pytest Tests

```bash
# Basic usage
python -m trim_telemetry.pytest

# With specific test files
python -m trim_telemetry.pytest tests/test_models.py

# With test discovery
python -m trim_telemetry.pytest tests/

# With pytest options
python -m trim_telemetry.pytest -v --tb=short
```

### Unittest Tests

```bash
# Basic usage (auto-discovers tests)
python -m trim_telemetry.unittest

# With specific test modules
python -m trim_telemetry.unittest test_models test_views

# With specific test classes
python -m trim_telemetry.unittest test_models.TestUserModel
```


### Docker Usage

```bash
# Django tests in Docker
docker-compose run --rm django python manage.py test --testrunner=trim_telemetry.django.TelemetryTestRunner

# With keepdb for faster runs
docker-compose run --rm django python manage.py test --testrunner=trim_telemetry.django.TelemetryTestRunner --keepdb

# Pytest tests in Docker
docker-compose run --rm django python -m trim_telemetry.pytest tests/
```

## Architecture

### 🏗️ **Clean Architecture**

The package uses a clean, modular architecture organized by framework:

- **`base_telemetry.py`**: Shared telemetry collection logic
- **`django/`**: Django framework integration
  - **`telemetry.py`**: Django-specific database and network monitoring
  - **`runner.py`**: Django test runner using shared telemetry
- **`pytest/`**: Pytest framework integration
  - **`runner.py`**: Pytest runner with telemetry collection
- **`unittest/`**: Unittest framework integration
  - **`runner.py`**: Unittest runner with telemetry collection


## Features

### 🎯 **Rich Telemetry Collection**
- **Database Query Analysis**: Per-test query isolation, duplicate query identification
- **Performance Metrics**: Accurate test duration tracking with millisecond precision
- **Network Call Monitoring**: Captures external API calls for unmocked test detection
- **Test Isolation**: Accurate per-test metrics without cross-test contamination

### 🔧 **Advanced Analytics**
- **Query Type Breakdown**: SELECT, INSERT, UPDATE, DELETE query categorization
- **Performance Tracking**: Test duration, database query counts, network call counts
- **Clean Output**: Raw telemetry data without judgment calls or complex calculations
- **Test Status Tracking**: Passed, failed, error, skipped status for each test

### 🚀 **Framework Support**
- **Django**: Custom test runner with full Django integration and database monitoring
- **Pytest**: Comprehensive pytest plugin with rich instrumentation
- **Unittest**: Enhanced unittest runner with telemetry collection
- **Docker Compatible**: Works seamlessly inside Docker containers

### 📋 **Schema & Documentation**
- **Versioned Schema**: Each record includes schema version for compatibility
- **Complete Documentation**: Detailed field descriptions and data types in [SCHEMA.md](SCHEMA.md)
- **Flattened Structure**: All fields at top level with clear prefixes (`db_`, `net_`)
- **NDJSON Format**: Newline Delimited JSON for streaming processing

## Telemetry Data

The package outputs comprehensive structured telemetry data for each test:

### 📊 **Flattened Telemetry Structure (Schema v1.0.0)**

```json
{
  "schema_version": "1.0.0",
  "run_id": "run_20250909_143808",
  "id": "test_user_creation (users.tests.test_models.UserTestCase.test_user_creation)",
  "name": "test_user_creation",
  "class": "UserTestCase", 
  "module": "users.tests.test_models",
  "file": "users/tests/test_models.py",
  "line": 0,
  "status": "passed",
  "test_duration_ms": 1250,
  "start_time": "2025-09-09T14:38:15.123456",
  "end_time": "2025-09-09T14:38:16.373456",
  
  "db_count": 15,
  "db_total_duration_ms": 245,
  "db_queries": [
    {
      "sql": "SELECT * FROM users WHERE email = 'test@example.com'",
      "duration_ms": 156
    }
  ],
  "db_duplicate_queries": [
    {
      "sql": "SELECT id FROM posts WHERE user_id = %s",
      "count": 3
    }
  ],
  "db_select_count": 12,
  "db_insert_count": 2,
  "db_update_count": 1,
  "db_delete_count": 0,
  "db_other_count": 0,
  "db_avg_duration_ms": 16,
  "db_max_duration_ms": 156,
  
  "net_total_calls": 0,
  "net_urls": []
}
```

### 🎯 **Key Telemetry Features**

#### **Database Query Analysis**
- **Per-test isolation**: Each test shows only its own queries
- **Query categorization**: Breakdown by SELECT/INSERT/UPDATE/DELETE
- **Duplicate detection**: Identifies repeated SQL statements
- **Performance metrics**: Average and maximum query durations in milliseconds
- **Clean output**: No judgment calls, just raw data for analysis

#### **Network Call Monitoring**
- **External call detection**: Captures URLs of external API calls
- **Unmocked test identification**: Helps identify tests that aren't properly mocked
- **Simple tracking**: Just captures URLs without timing or blocking
- **Thread-safe**: Works across multiple test threads

#### **Performance Tracking**
- **Duration precision**: All durations in milliseconds with integer precision
- **Test status**: Passed, failed, error, skipped status for each test
- **Run correlation**: Unique run ID to correlate all telemetry from a test run
- **Clean metrics**: No complex calculations, just raw performance data

## Output Format

The telemetry data is written to a **`.telemetry/`** folder in the current working directory. Each test run creates a new file named with the run ID and timestamp in **NDJSON format** (Newline Delimited JSON).

**File structure:**
```
.telemetry/
├── run_20250909_143808.ndjson
├── run_20250909_144512.ndjson
└── run_20250909_145123.ndjson
```

**File contents (e.g., `run_20250909_143808.ndjson`):**
```
{"schema_version": "1.0.0", "run_id": "run_20250909_143808", "id": "test_user_creation", "name": "test_user_creation", "status": "passed", "test_duration_ms": 1250, ...}
{"schema_version": "1.0.0", "run_id": "run_20250909_143808", "id": "test_user_deletion", "name": "test_user_deletion", "status": "passed", "test_duration_ms": 890, ...}
{"schema_version": "1.0.0", "run_id": "run_20250909_143808", "id": "test_user_update", "name": "test_user_update", "status": "failed", "test_duration_ms": 2100, ...}
```

**Note:** Summary data is calculated by analysis tools from individual test records.

### **Folder-Based Output Benefits:**
- **Organized**: All telemetry files in one `.telemetry/` folder
- **Multiple Runs**: Each test run gets its own file (no overwrites)
- **Timestamped**: Files named with run ID and datetime for easy identification
- **Clean Separation**: Test output goes to stdout, telemetry goes to files
- **Persistent Data**: Telemetry is saved for later analysis
- **No Interference**: Doesn't mix with test output or logs
- **Easy Access**: Go tool can read from specific files or process all files
- **Streaming**: Data can be processed line-by-line as tests execute
- **Efficient**: No need to parse large JSON arrays
- **Go-friendly**: Perfect for Go's `json.Decoder` with `Decode()` in a loop

### **Go Integration Example:**
```go
package main

import (
    "encoding/json"
    "fmt"
    "os"
)

type TestResult struct {
    SchemaVersion     string `json:"schema_version"`
    RunID            string `json:"run_id"`
    ID               string `json:"id"`
    Name             string `json:"name"`
    Status           string `json:"status"`
    TestDurationMs   int    `json:"test_duration_ms"`
    DbCount          int    `json:"db_count"`
    NetTotalCalls    int    `json:"net_total_calls"`
    // ... other fields
}

func main() {
    decoder := json.NewDecoder(os.Stdin)
    
    for {
        var result TestResult
        if err := decoder.Decode(&result); err != nil {
            break // End of stream
        }
        
        // Check schema version
        if result.SchemaVersion != "1.0.0" {
            fmt.Printf("Warning: Unsupported schema version %s\n", result.SchemaVersion)
            continue
        }
        
        // Process each test result as it arrives
        fmt.Printf("Test %s: %s (%dms, %d DB queries, %d network calls)\n", 
            result.Name, result.Status, result.TestDurationMs, result.DbCount, result.NetTotalCalls)
    }
}
```

### **Usage with Go Analysis Tool:**
```bash
# Run tests (telemetry automatically written to .telemetry/ folder)
python manage.py test --testrunner=trim_telemetry.django.TelemetryTestRunner

# Process latest telemetry file
go run analysis.go .telemetry/run_20250909_143808.ndjson

# Process all telemetry files
go run analysis.go .telemetry/

# Or stream latest telemetry as it's written
tail -f .telemetry/run_20250909_143808.ndjson | go run analysis.go
```

### 📈 **Interpreting Telemetry Data**

#### **Test Performance**
- **test_duration_ms**: Test execution time in milliseconds (integer precision)
- **status**: Test result (passed, failed, error, skipped)
- **run_id**: Unique identifier to correlate all telemetry from a single test run

#### **Database Analysis**
- **db_count**: Number of database queries executed during the test
- **db_total_duration_ms**: Total time spent on database queries
- **db_queries**: Array of all SQL queries executed (for debugging)
- **db_duplicate_queries**: Array of duplicate queries (same SQL, different parameters)
- **db_select_count**: Number of SELECT queries
- **db_insert_count**: Number of INSERT queries
- **db_update_count**: Number of UPDATE queries
- **db_delete_count**: Number of DELETE queries
- **db_other_count**: Number of other query types
- **db_avg_duration_ms**: Average query duration in milliseconds
- **db_max_duration_ms**: Slowest query duration in milliseconds

#### **Network Monitoring**
- **net_total_calls**: Number of external HTTP calls made during the test
- **net_urls**: List of URLs that were called (helps identify unmocked tests)

## Schema Documentation

For complete field descriptions, data types, and schema versioning information, see [SCHEMA.md](SCHEMA.md).

### **Key Schema Features:**
- **Versioned**: Each record includes `schema_version` for compatibility
- **Flattened**: All fields are at the top level with clear prefixes (`db_`, `net_`)
- **NDJSON**: Newline Delimited JSON format for streaming processing
- **Self-describing**: Each record contains all necessary metadata

## Troubleshooting

### Common Issues

**Database connection errors:**
```bash
# Use --keepdb flag to reuse existing test databases
python manage.py test --testrunner=trim_telemetry.django.TelemetryTestRunner --keepdb
```

**Tests not discovered:**
```bash
# Ensure you're in the correct directory with your test files
# Check that your test files follow naming conventions (test_*.py)
```

**Telemetry files not created:**
```bash
# Check write permissions in the current directory
# Ensure the .telemetry/ folder can be created
```

### Getting Help

- Check the [Schema Documentation](SCHEMA.md) for detailed field descriptions
- Review the telemetry output format and field meanings
- Ensure your test framework is supported (Django 3.2+, pytest 6.0+)

## Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

### Development Setup

```bash
# Install in development mode
pip install -e .

# Run tests
pytest

# Format code
black trim_telemetry/
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Changelog

### v1.0.0
- Initial release with flattened schema
- Support for Django, pytest, and unittest
- Database query monitoring
- Network call detection
- NDJSON output format
- Schema versioning
