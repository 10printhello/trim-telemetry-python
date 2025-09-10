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

### Django Tests (Recommended)

#### **Using the New Test Runner**

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

### Pytest Tests (New)

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

### Unittest Tests (New)

```bash
# Basic usage (auto-discovers tests)
python -m trim_telemetry.unittest

# With specific test modules
python -m trim_telemetry.unittest test_models test_views

# With specific test classes
python -m trim_telemetry.unittest test_models.TestUserModel
```


### With Trim CLI

```bash
# Install the package in your Python environment
pip install trim-telemetry

# Django with new test runner (recommended)
make collect TEST_COMMAND="python manage.py test --testrunner=trim_telemetry.django.TelemetryTestRunner"

# Django with direct execution
make collect TEST_COMMAND="python -m trim_telemetry.django"

# Pytest with new runner
make collect TEST_COMMAND="python -m trim_telemetry.pytest tests/"

# Unittest with new runner
make collect TEST_COMMAND="python -m trim_telemetry.unittest"

# Docker Django with new test runner
make collect TEST_COMMAND="ENVIRONMENT=testing python manage.py test --testrunner=trim_telemetry.django.TelemetryTestRunner"

```

## Architecture

### 🏗️ **New Clean Architecture (Recommended)**

The package now uses a clean, modular architecture organized by framework:

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
- **Statistical Analysis**: Per-test metrics with clean telemetry output
- **Test Status Tracking**: Passed, failed, error, skipped status for each test

### 🚀 **Framework Support**
- **Django**: Custom test runner with full Django integration and database monitoring
- **Pytest**: Comprehensive pytest plugin with rich instrumentation
- **Unittest**: Enhanced unittest runner with telemetry collection
- **Docker Compatible**: Works seamlessly inside Docker containers

## Telemetry Data

The package outputs comprehensive structured telemetry data for each test:

### 📊 **Clean Telemetry Structure**

```json
{
  "run_id": "run_20250909_143808",
  "id": "test_user_creation (users.tests.test_models.UserTestCase.test_user_creation)",
  "name": "test_user_creation",
  "class": "UserTestCase", 
  "module": "users.tests.test_models",
  "file": "users/tests/test_models.py",
  "line": 0,
  "status": "passed",
  "duration_ms": 1250,
  "start_time": "2025-09-09T14:38:15.123456",
  "end_time": "2025-09-09T14:38:16.373456",
  
  "database": {
    "count": 15,
    "total_duration_ms": 245,
    "queries": [
      {
        "sql": "SELECT * FROM users WHERE email = 'test@example.com'",
        "duration_ms": 156
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
    "avg_duration_ms": 16,
    "max_duration_ms": 156
  },
  
  "network": {
    "total_calls": 0,
    "urls": []
  },
  
  "test_performance": {
    "duration_ms": 1250
  }
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
{"run_id": "run_20250909_143808", "id": "test_user_creation", "name": "test_user_creation", "status": "passed", "test_duration_ms": 1250, ...}
{"run_id": "run_20250909_143808", "id": "test_user_deletion", "name": "test_user_deletion", "status": "passed", "test_duration_ms": 890, ...}
{"run_id": "run_20250909_143808", "type": "test_run_summary", "total_tests": 25, "passed_tests": 23, "failed_tests": 2, "skipped_tests": 0, "exit_code": 1}
```

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
    RunID     string `json:"run_id"`
    ID        string `json:"id"`
    Name      string `json:"name"`
    Status    string `json:"status"`
    Duration  int    `json:"duration_ms"`
    // ... other fields
}

func main() {
    decoder := json.NewDecoder(os.Stdin)
    
    for {
        var result TestResult
        if err := decoder.Decode(&result); err != nil {
            break // End of stream
        }
        
        // Process each test result as it arrives
        fmt.Printf("Test %s: %s (%dms)\n", result.Name, result.Status, result.Duration)
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

## Development

```bash
# Install in development mode
pip install -e .

# Run tests
pytest

# Format code
black trim_telemetry/
```
