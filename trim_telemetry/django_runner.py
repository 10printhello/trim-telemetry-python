"""
Django test runner with minimal telemetry
"""

import json
import sys
import time
import unittest
from datetime import datetime
from django.test.runner import DiscoverRunner
from django.test.utils import CaptureQueriesContext
from django.db import connection, reset_queries
from django.conf import settings


class TelemetryTestResult(unittest.TextTestResult):
    """Custom test result class for telemetry collection."""

    def __init__(self, run_id, *args, **kwargs):
        # Ensure verbosity is an integer, default to 1 if None
        verbosity = kwargs.get("verbosity", 1)
        if verbosity is None:
            verbosity = 1
        kwargs["verbosity"] = verbosity

        # Ensure stream is not None, default to sys.stdout
        if kwargs.get("stream") is None:
            kwargs["stream"] = sys.stdout

        super().__init__(*args, **kwargs)
        self.run_id = run_id
        self.test_status = {}
        self.test_timings = {}
        self.test_queries = {}  # Store queries for each test

        # Enable query logging if not already enabled
        self._ensure_query_logging_enabled()

    def _ensure_query_logging_enabled(self):
        """Ensure Django query logging is enabled."""
        try:
            # Reset any existing queries
            reset_queries()
            
            # Enable query logging in settings (Django best practice)
            if not getattr(settings, "DEBUG", False):
                settings.DEBUG = True
                print("DEBUG: Enabled DEBUG mode for query logging", flush=True)

            print("DEBUG: Query logging enabled", flush=True)
        except Exception as e:
            print(f"DEBUG: Error enabling query logging: {e}", flush=True)

    def startTest(self, test):
        super().startTest(test)
        test_id = str(test)
        self.test_status[test_id] = "running"
        self.test_timings[test_id] = time.time()

        # Reset queries before each test (Django best practice)
        reset_queries()
        
        # Start capturing database queries for this test using CaptureQueriesContext
        self.test_queries[test_id] = CaptureQueriesContext(connection)
        self.test_queries[test_id].__enter__()

        # Add progress indicator for long-running tests
        if hasattr(self, "_test_count"):
            self._test_count += 1
        else:
            self._test_count = 1

        # Print progress every 50 tests
        if self._test_count % 50 == 0:
            print(f"DEBUG: Progress - {self._test_count} tests started", flush=True)

    def addSuccess(self, test):
        super().addSuccess(test)
        self.test_status[str(test)] = "passed"
        self._output_test_telemetry(test, "passed")

    def addError(self, test, err):
        super().addError(test, err)
        self.test_status[str(test)] = "error"
        self._output_test_telemetry(test, "error")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.test_status[str(test)] = "failed"
        self._output_test_telemetry(test, "failed")

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.test_status[str(test)] = "skipped"
        self._output_test_telemetry(test, "skipped")

    def _output_test_telemetry(self, test, status):
        """Output telemetry for a single test."""
        test_id = str(test)
        end_time = time.time()
        start_time = self.test_timings.get(test_id, end_time)
        duration_ms = round((end_time - start_time) * 1000)

        # Collect database telemetry and clean up
        database_telemetry = self._collect_database_telemetry(test_id)
        self._cleanup_test_queries(test_id)

        test_telemetry = {
            "run_id": self.run_id,
            "id": test_id,
            "name": getattr(test, "_testMethodName", test_id),
            "class": test.__class__.__name__,
            "module": test.__class__.__module__,
            "file": test.__class__.__module__.replace(".", "/") + ".py",
            "line": 0,
            "status": status,
            "duration_ms": duration_ms,
            "start_time": datetime.fromtimestamp(start_time).isoformat(),
            "end_time": datetime.fromtimestamp(end_time).isoformat(),
            "database": database_telemetry,
            "network": {
                "calls_attempted": 0,
                "calls_blocked": 0,
                "total_duration": 0,
                "external_calls": [],
                "blocked_calls": [],
            },
            "test_performance": {
                "duration_ms": duration_ms,
            },
        }
        print(f"TEST_RESULT:{json.dumps(test_telemetry)}", flush=True)

        # Add completion progress indicator
        if hasattr(self, "_completed_count"):
            self._completed_count += 1
        else:
            self._completed_count = 1

        # Print completion progress every 100 tests
        if self._completed_count % 100 == 0:
            print(
                f"DEBUG: Progress - {self._completed_count} tests completed", flush=True
            )

    def _cleanup_test_queries(self, test_id):
        """Clean up query context for a test."""
        try:
            query_context = self.test_queries.get(test_id)
            if query_context:
                query_context.__exit__(None, None, None)  # Exit the context manager
                del self.test_queries[test_id]
        except Exception as e:
            print(f"DEBUG: Error cleaning up queries for {test_id}: {e}", flush=True)

    def _collect_database_telemetry(self, test_id):
        """Collect database telemetry for a test."""
        try:
            # Get the CaptureQueriesContext for this test
            query_context = self.test_queries.get(test_id)
            if not query_context:
                return {
                    "count": 0,
                    "total_duration_ms": 0,
                    "slow_queries": [],
                    "duplicate_queries": [],
                    "query_types": {
                        "SELECT": 0,
                        "INSERT": 0,
                        "UPDATE": 0,
                        "DELETE": 0,
                        "OTHER": 0,
                    },
                    "avg_duration_ms": 0,
                    "max_duration_ms": 0,
                }

            # Get the captured queries from the context
            test_queries = query_context.captured_queries
            query_count = len(test_queries)

            # Debug: Show query count for this test
            if query_count > 0:
                print(f"DEBUG: Test {test_id} had {query_count} queries", flush=True)

            if query_count == 0:
                return {
                    "count": 0,
                    "total_duration_ms": 0,
                    "slow_queries": [],
                    "duplicate_queries": [],
                    "query_types": {
                        "SELECT": 0,
                        "INSERT": 0,
                        "UPDATE": 0,
                        "DELETE": 0,
                        "OTHER": 0,
                    },
                    "avg_duration_ms": 0,
                    "max_duration_ms": 0,
                }

            # Analyze queries
            total_duration = 0
            slow_queries = []
            query_types = {
                "SELECT": 0,
                "INSERT": 0,
                "UPDATE": 0,
                "DELETE": 0,
                "OTHER": 0,
            }
            query_signatures = {}
            max_duration = 0

            for query in test_queries:
                duration = query.get("time", 0)
                total_duration += duration
                max_duration = max(max_duration, duration)

                # Track slow queries (> 10ms)
                if duration > 0.01:  # 10ms
                    slow_queries.append(
                        {
                            "sql": query.get("sql", "")[:200] + "..."
                            if len(query.get("sql", "")) > 200
                            else query.get("sql", ""),
                            "duration_ms": round(duration * 1000),
                        }
                    )

                # Count query types
                sql = query.get("sql", "").upper().strip()
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

                # Track duplicate queries (same SQL)
                sql_signature = sql[:100]  # First 100 chars for signature
                if sql_signature in query_signatures:
                    query_signatures[sql_signature] += 1
                else:
                    query_signatures[sql_signature] = 1

            # Find duplicate queries
            duplicate_queries = []
            for signature, count in query_signatures.items():
                if count > 1:
                    duplicate_queries.append(
                        {
                            "sql": signature + "..."
                            if len(signature) > 100
                            else signature,
                            "count": count,
                        }
                    )

            # Calculate averages
            avg_duration = (total_duration / query_count) if query_count > 0 else 0

            return {
                "count": query_count,
                "total_duration_ms": round(total_duration * 1000),
                "slow_queries": slow_queries,
                "duplicate_queries": duplicate_queries,
                "query_types": query_types,
                "avg_duration_ms": round(avg_duration * 1000),
                "max_duration_ms": round(max_duration * 1000),
            }

        except Exception as e:
            # If there's any error collecting database telemetry, return zeros
            print(
                f"DEBUG: Error collecting database telemetry for {test_id}: {e}",
                flush=True,
            )
            return {
                "count": 0,
                "total_duration_ms": 0,
                "slow_queries": [],
                "duplicate_queries": [],
                "query_types": {
                    "SELECT": 0,
                    "INSERT": 0,
                    "UPDATE": 0,
                    "DELETE": 0,
                    "OTHER": 0,
                },
                "avg_duration_ms": 0,
                "max_duration_ms": 0,
            }


class TrimTelemetryRunner(DiscoverRunner):
    """Django test runner with minimal telemetry collection."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        print(
            f"DEBUG: TrimTelemetryRunner initialized with run_id: {self.run_id}",
            flush=True,
        )

    def run_suite(self, suite, **kwargs):
        """Run test suite with per-test telemetry."""
        print(f"DEBUG: Running suite with {suite.countTestCases()} tests", flush=True)

        # Use our custom result class
        result = TelemetryTestResult(
            self.run_id,
            stream=kwargs.get("stream"),
            descriptions=kwargs.get("descriptions"),
            verbosity=kwargs.get("verbosity"),
        )

        # Run the suite
        suite.run(result)

        # Output basic telemetry for each test
        if hasattr(result, "testsRun"):
            print(f"DEBUG: Tests completed: {result.testsRun}", flush=True)

        return result

    def run_tests(self, test_labels=None, **kwargs):
        """Run tests with minimal telemetry."""
        print(f"DEBUG: run_tests called with test_labels: {test_labels}", flush=True)

        # Use standard Django behavior
        result = super().run_tests(test_labels, **kwargs)

        # Output basic summary
        if hasattr(result, "testsRun"):
            total_tests = result.testsRun
            failed_tests = len(result.failures) + len(result.errors)
            skipped_tests = len(result.skipped) if hasattr(result, "skipped") else 0
            passed_tests = total_tests - failed_tests - skipped_tests

            summary_data = {
                "run_id": self.run_id,
                "type": "test_run_summary",
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": failed_tests,
                "skipped_tests": skipped_tests,
                "exit_code": 0 if result.wasSuccessful() else 1,
            }
            print(f"TEST_SUMMARY:{json.dumps(summary_data)}", flush=True)

        return result
