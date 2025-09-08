"""
Django test runner with rich telemetry collection
"""

import json
import os
import time
import unittest
from datetime import datetime
from django.test.runner import DiscoverRunner
from django.db import connection
from .base_collector import BaseTelemetryCollector

# Try to import coverage tools
try:
    import coverage

    COVERAGE_AVAILABLE = True
except ImportError:
    COVERAGE_AVAILABLE = False


class TrimTelemetryRunner(DiscoverRunner):
    """Django test runner with rich telemetry collection."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.telemetry_collector = BaseTelemetryCollector()
        # Block network calls
        self.original_socket = self.telemetry_collector.block_network_calls()
        # Track query counts per test for isolation
        self.test_query_counts = {}
        # Initialize coverage collection
        self.coverage_collector = self._init_coverage_collector()
        self.test_coverage_data = {}
        # Track test durations for percentile calculations
        self.test_durations = []

    def run_suite(self, suite, **kwargs):
        """Run test suite with instrumentation."""

        class InstrumentedTestResult(unittest.TextTestResult):
            def __init__(self, telemetry_collector, runner, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.telemetry_collector = telemetry_collector
                self.runner = runner
                self.test_status = {}

            def startTest(self, test):
                super().startTest(test)
                self.telemetry_collector.start_test(test)
                # Capture initial query count for this test
                test_id = str(test)
                self.runner.test_query_counts[test_id] = len(connection.queries)
                # Start coverage collection for this test
                self.runner._start_test_coverage(test_id)

            def addSuccess(self, test):
                super().addSuccess(test)
                self.test_status[str(test)] = "passed"

            def addError(self, test, err):
                super().addError(test, err)
                self.test_status[str(test)] = "error"

            def addFailure(self, test, err):
                super().addFailure(test, err)
                self.test_status[str(test)] = "failed"

            def addSkip(self, test, reason):
                super().addSkip(test, reason)
                self.test_status[str(test)] = "skipped"

            def stopTest(self, test):
                # Get database query info for THIS test only
                test_id = str(test)
                initial_query_count = self.runner.test_query_counts.get(test_id, 0)

                # Calculate queries executed during this test
                test_queries = connection.queries[initial_query_count:]
                queries = len(test_queries)
                query_time = sum(float(q["time"]) for q in test_queries)

                # Get test timing
                if self.telemetry_collector.current_test_start:
                    end_time = time.time()
                    start_time = self.telemetry_collector.current_test_start
                    duration = (end_time - start_time) * 1000  # Convert to milliseconds

                    # Track duration for percentile calculations
                    self.runner.test_durations.append(duration)

                    # Get test status
                    test_id = str(test)
                    status = self.test_status.get(test_id, "passed")

                    # Create rich telemetry data
                    test_telemetry = {
                        "id": test_id,
                        "name": getattr(test, "_testMethodName", test_id),
                        "class": test.__class__.__name__,
                        "module": test.__class__.__module__,
                        "file": test.__class__.__module__.replace(".", "/") + ".py",
                        "line": 0,  # Would need to extract from test method
                        "status": status,
                        "duration": round(duration),
                        "start_time": datetime.fromtimestamp(start_time).isoformat(),
                        "end_time": datetime.fromtimestamp(end_time).isoformat(),
                        "tags": [],
                        "fixtures": [],
                        "database_queries": self.runner._analyze_database_queries(
                            test_queries, query_time
                        ),
                        "http_calls": {
                            "count": len(
                                self.telemetry_collector.network_call_attempts
                            ),
                            "total_duration": 0,
                            "external_calls": self.telemetry_collector.network_call_attempts.copy(),
                            "blocked_calls": self.telemetry_collector.network_call_attempts.copy(),
                        },
                        "performance": {
                            "is_slow": duration > 1000,  # > 1 second
                            "is_db_heavy": queries > 50,
                            "is_network_heavy": len(
                                self.telemetry_collector.network_call_attempts
                            )
                            > 0,
                            "has_blocked_network_calls": len(
                                self.telemetry_collector.network_call_attempts
                            )
                            > 0,
                            "current_duration": round(duration),
                            "avg_duration": self.runner._calculate_average_duration(),
                            "median_duration": self.runner._calculate_percentile(50),
                            "p95_duration": self.runner._calculate_percentile(95),
                            "p99_duration": self.runner._calculate_percentile(99),
                            "total_tests_run": len(self.runner.test_durations),
                            "flags": self.runner._generate_performance_flags(
                                duration, queries, test_queries
                            ),
                        },
                        "coverage": self.runner._collect_test_coverage(test_id),
                        "logs": [],
                        "metadata": {},
                    }

                    # Output telemetry data
                    print(f"TEST_RESULT:{json.dumps(test_telemetry)}")

                    # Clear network calls for next test
                    self.telemetry_collector.network_call_attempts = []

                super().stopTest(test)

        # Create test runner with instrumentation
        runner = unittest.TextTestRunner(
            verbosity=self.verbosity,
            resultclass=lambda *args, **kwargs: InstrumentedTestResult(
                self.telemetry_collector, self, *args, **kwargs
            ),
        )

        return runner.run(suite)

    def _analyze_database_queries(self, test_queries, total_query_time):
        """Analyze database queries for rich telemetry data."""
        if not test_queries:
            return {
                "count": 0,
                "total_duration": 0,
                "slow_queries": [],
                "duplicate_queries": [],
                "query_types": {
                    "SELECT": 0,
                    "INSERT": 0,
                    "UPDATE": 0,
                    "DELETE": 0,
                    "OTHER": 0,
                },
                "avg_duration": 0,
                "max_duration": 0,
            }

        # Analyze query types
        query_types = {"SELECT": 0, "INSERT": 0, "UPDATE": 0, "DELETE": 0, "OTHER": 0}
        slow_queries = []
        query_durations = []
        sql_queries = {}  # For duplicate detection

        for query in test_queries:
            sql = query["sql"].strip().upper()
            duration = float(query["time"])
            query_durations.append(duration)

            # Categorize query type
            if sql.startswith("SELECT"):
                query_types["SELECT"] += 1
            elif sql.startswith("INSERT"):
                query_types["INSERT"] += 1
            elif sql.startswith("UPDATE"):
                query_types["UPDATE"] += 1
            elif sql.startswith("DELETE"):
                query_types["DELETE"] += 1
            else:
                query_types["OTHER"] += 1

            # Track slow queries (> 100ms)
            if duration > 0.1:
                slow_queries.append(
                    {
                        "sql": query["sql"],
                        "time": duration,
                        "duration": round(duration * 1000),  # Convert to milliseconds
                    }
                )

            # Track duplicate queries (same SQL)
            if sql in sql_queries:
                sql_queries[sql] += 1
            else:
                sql_queries[sql] = 1

        # Find duplicate queries
        duplicate_queries = [
            {"sql": sql, "count": count}
            for sql, count in sql_queries.items()
            if count > 1
        ]

        return {
            "count": len(test_queries),
            "total_duration": round(total_query_time * 1000),  # Convert to milliseconds
            "slow_queries": slow_queries,
            "duplicate_queries": duplicate_queries,
            "query_types": query_types,
            "avg_duration": round(
                (sum(query_durations) / len(query_durations)) * 1000, 2
            ),
            "max_duration": round(max(query_durations) * 1000, 2),
        }

    def _generate_performance_flags(self, duration, query_count, test_queries):
        """Generate performance flags based on test metrics."""
        flags = []

        # Duration flags
        if duration > 5000:
            flags.append("very_slow")
        elif duration > 1000:
            flags.append("slow")

        # Database query flags
        if query_count > 100:
            flags.append("high_db_queries")
        elif query_count > 50:
            flags.append("moderate_db_queries")

        # Network call flags
        if len(self.telemetry_collector.network_call_attempts) > 0:
            flags.append("network_calls_blocked")

        # Query-specific flags
        if test_queries:
            slow_query_count = len([q for q in test_queries if float(q["time"]) > 0.1])
            if slow_query_count > 0:
                flags.append(f"has_slow_queries_{slow_query_count}")

            # Check for N+1 query patterns (multiple similar SELECT queries)
            select_queries = [
                q for q in test_queries if q["sql"].strip().upper().startswith("SELECT")
            ]
            if len(select_queries) > 10:
                flags.append("potential_n_plus_1_queries")

        return flags

    def _calculate_percentile(self, percentile):
        """Calculate percentile from test durations."""
        if not self.test_durations:
            return 0

        # Sort durations
        sorted_durations = sorted(self.test_durations)
        n = len(sorted_durations)

        if n == 1:
            return round(sorted_durations[0])

        # Calculate percentile index
        index = (percentile / 100.0) * (n - 1)

        if index.is_integer():
            # Exact index
            return round(sorted_durations[int(index)])
        else:
            # Interpolate between two values
            lower_index = int(index)
            upper_index = lower_index + 1
            weight = index - lower_index

            lower_value = sorted_durations[lower_index]
            upper_value = sorted_durations[upper_index]

            interpolated = lower_value + weight * (upper_value - lower_value)
            return round(interpolated)

    def _calculate_average_duration(self):
        """Calculate average duration from test durations."""
        if not self.test_durations:
            return 0
        return round(sum(self.test_durations) / len(self.test_durations))

    def _init_coverage_collector(self):
        """Initialize coverage collection if available."""
        if not COVERAGE_AVAILABLE:
            return None

        try:
            # Create coverage instance
            cov = coverage.Coverage(
                source=["."],  # Cover current directory
                omit=[
                    "*/tests/*",
                    "*/test_*",
                    "*/migrations/*",
                    "*/venv/*",
                    "*/env/*",
                    "*/__pycache__/*",
                    "*/node_modules/*",
                ],
            )
            return cov
        except Exception as e:
            print(f"DEBUG: Failed to initialize coverage: {e}", flush=True)
            return None

    def _start_test_coverage(self, test_id):
        """Start coverage collection for a specific test."""
        if not self.coverage_collector:
            return

        try:
            # Start coverage collection
            self.coverage_collector.start()
            self.test_coverage_data[test_id] = {
                "started": True,
                "start_time": time.time(),
            }
        except Exception as e:
            print(
                f"DEBUG: Failed to start coverage for test {test_id}: {e}", flush=True
            )

    def _collect_test_coverage(self, test_id):
        """Collect coverage data for a specific test."""
        if not self.coverage_collector or test_id not in self.test_coverage_data:
            return {
                "lines_covered": 0,
                "lines_total": 0,
                "coverage_percent": 0.0,
                "files": [],
                "status": "not_available",
            }

        try:
            # Stop coverage collection
            self.coverage_collector.stop()

            # Get coverage data
            coverage_data = self.coverage_collector.get_data()

            # Calculate coverage metrics
            total_lines = 0
            covered_lines = 0
            file_coverage = []

            for filename in coverage_data.measured_files():
                if not filename.endswith(".py"):
                    continue

                # Get line coverage for this file using Analysis
                try:
                    from coverage.analysis import Analysis
                    analysis = Analysis(coverage_data, filename)
                    lines = analysis.statements
                    missing = analysis.missing
                    
                    if lines:
                        file_total = len(lines)
                        file_covered = file_total - len(missing)
                    else:
                        continue
                except Exception:
                    # Fallback to basic coverage data
                    lines = coverage_data.lines(filename)
                    if lines:
                        file_total = len(lines)
                        file_covered = file_total  # Assume all lines covered if we can't get missing
                    else:
                        continue

                total_lines += file_total
                covered_lines += file_covered

                file_coverage.append(
                        {
                            "file": filename,
                            "lines_covered": file_covered,
                            "lines_total": file_total,
                            "coverage_percent": round(
                                (file_covered / file_total) * 100, 2
                            )
                            if file_total > 0
                            else 0,
                            "missing_lines": list(missing) if 'missing' in locals() and missing else [],
                        }
                    )

            coverage_percent = (
                round((covered_lines / total_lines) * 100, 2)
                if total_lines > 0
                else 0.0
            )

            # Restart coverage for next test
            self.coverage_collector.start()

            return {
                "lines_covered": covered_lines,
                "lines_total": total_lines,
                "coverage_percent": coverage_percent,
                "files": file_coverage,
                "status": "collected",
            }

        except Exception as e:
            print(
                f"DEBUG: Failed to collect coverage for test {test_id}: {e}", flush=True
            )
            return {
                "lines_covered": 0,
                "lines_total": 0,
                "coverage_percent": 0.0,
                "files": [],
                "status": "error",
                "error": str(e),
            }

    def run_tests(self, test_labels=None, **kwargs):
        """Run tests with telemetry collection."""
        import signal
        import sys

        # Store the summary data to output it even if we get terminated
        summary_data = None

        def signal_handler(signum, frame):
            """Handle termination signals to ensure TEST_SUMMARY is output."""
            if summary_data:
                print(f"TEST_SUMMARY:{json.dumps(summary_data)}", flush=True)
            sys.exit(0)

        # Register signal handlers
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        self.telemetry_collector.start_test_run()

        try:
            # Run tests with instrumentation using run_suite to get proper test result
            suite = self.build_suite(test_labels)
            result = self.run_suite(suite)

            # Output final summary with proper test counts
            total_tests = result.testsRun
            passed_tests = total_tests - len(result.failures) - len(result.errors)
            failed_tests = len(result.failures) + len(result.errors)
            skipped_tests = len(result.skipped) if hasattr(result, "skipped") else 0

            summary_data = {
                "type": "test_run_summary",
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "skipped_tests": skipped_tests,
                "exit_code": 0 if result.wasSuccessful() else 1,
            }
            print(f"TEST_SUMMARY:{json.dumps(summary_data)}", flush=True)
            print("DEBUG: TEST_SUMMARY output completed", flush=True)

            return len(result.failures) + len(result.errors)

        except Exception as e:
            # Output a summary even if there was an error
            if summary_data is None:
                summary_data = {
                    "type": "test_run_summary",
                    "total_tests": 0,
                    "passed_tests": 0,
                    "failed_tests": 1,
                    "skipped_tests": 0,
                    "exit_code": 1,
                    "error": str(e),
                }
            print(f"TEST_SUMMARY:{json.dumps(summary_data)}", flush=True)
            print(f"DEBUG: Error occurred: {e}", flush=True)
            raise

        finally:
            # Restore network calls
            self.telemetry_collector.restore_network_calls(self.original_socket)
            # Clean up coverage collection
            if self.coverage_collector:
                try:
                    self.coverage_collector.stop()
                except Exception as e:
                    print(f"DEBUG: Error stopping coverage collector: {e}", flush=True)
