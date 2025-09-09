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
from django.test.utils import CaptureQueriesContext
from .base_collector import BaseTelemetryCollector


class TrimTelemetryRunner(DiscoverRunner):
    """Django test runner with rich telemetry collection."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.telemetry_collector = BaseTelemetryCollector()
        # Generate unique run ID for this test run
        self.run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        # Block network calls
        self.original_socket = self.telemetry_collector.block_network_calls()
        # Track query counts per test for isolation
        self.test_query_counts = {}
        # Track query contexts for each test
        self.test_query_contexts = {}
        # Track test durations for percentile calculations
        self.test_durations = []

        # Debug: Print discovery settings
        print(f"DEBUG: Test discovery settings:", flush=True)
        print(f"  - verbosity: {self.verbosity}", flush=True)
        print(f"  - interactive: {self.interactive}", flush=True)
        print(f"  - keepdb: {self.keepdb}", flush=True)
        print(f"  - debug_mode: {self.debug_mode}", flush=True)

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
                # Start query capture for this test
                test_id = str(test)
                # Use CaptureQueriesContext for more reliable query capture
                query_context = CaptureQueriesContext(connection)
                query_context.__enter__()
                self.runner.test_query_contexts[test_id] = query_context

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

                # Get captured queries for this test
                query_context = self.runner.test_query_contexts.get(test_id)
                if query_context:
                    query_context.__exit__(None, None, None)
                    test_queries = query_context.captured_queries
                    queries = len(test_queries)
                    query_time = sum(float(q["time"]) for q in test_queries)
                else:
                    # Fallback to connection.queries if CaptureQueriesContext failed
                    test_queries = connection.queries
                    queries = len(test_queries)
                    query_time = sum(float(q["time"]) for q in test_queries)

                # Debug: Log query information
                print(
                    f"DEBUG: Test {test_id} - Captured queries: {queries}, Query time: {query_time}ms",
                    flush=True,
                )

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
                        "run_id": self.runner.run_id,
                        "id": test_id,
                        "name": getattr(test, "_testMethodName", test_id),
                        "class": test.__class__.__name__,
                        "module": test.__class__.__module__,
                        "file": test.__class__.__module__.replace(".", "/") + ".py",
                        "line": 0,  # Would need to extract from test method
                        "status": status,
                        "duration_ms": round(duration),
                        "start_time": datetime.fromtimestamp(start_time).isoformat(),
                        "end_time": datetime.fromtimestamp(end_time).isoformat(),
                        "tags": [],
                        "fixtures": [],
                        "database": self.runner._analyze_database_queries(
                            test_queries, query_time
                        ),
                        "network": {
                            "calls_attempted": len(
                                self.telemetry_collector.network_call_attempts
                            ),
                            "calls_blocked": len(
                                self.telemetry_collector.network_call_attempts
                            ),
                            "total_duration": 0,
                            "external_calls": self.telemetry_collector.network_call_attempts.copy(),
                            "blocked_calls": self.telemetry_collector.network_call_attempts.copy(),
                        },
                        "test_performance": {
                            "duration_ms": round(duration),
                        },
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
                        "duration_ms": round(
                            duration * 1000
                        ),  # Convert to milliseconds
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
            "total_duration_ms": round(
                total_query_time * 1000
            ),  # Convert to milliseconds
            "slow_queries": slow_queries,
            "duplicate_queries": duplicate_queries,
            "query_types": query_types,
            "avg_duration_ms": round(
                (sum(query_durations) / len(query_durations)) * 1000
            ),
            "max_duration_ms": round(max(query_durations) * 1000),
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
            # Debug: Print test labels being used
            print(f"DEBUG: Test labels: {test_labels}", flush=True)

            # Run tests with instrumentation using run_suite to get proper test result
            suite = self.build_suite(test_labels)

            # Debug: Count tests in suite
            total_tests_in_suite = suite.countTestCases()
            print(f"DEBUG: Suite contains {total_tests_in_suite} tests", flush=True)

            # Debug: Try to get more info about the suite
            if hasattr(suite, "_tests"):
                print(
                    f"DEBUG: Suite has {len(suite._tests)} top-level test groups",
                    flush=True,
                )
                for i, test_group in enumerate(suite._tests[:5]):  # Show first 5
                    if hasattr(test_group, "countTestCases"):
                        print(
                            f"  Group {i}: {test_group.countTestCases()} tests",
                            flush=True,
                        )

            # Debug: Compare with standard Django runner
            from django.test.runner import DiscoverRunner

            standard_runner = DiscoverRunner()
            standard_suite = standard_runner.build_suite(test_labels)
            standard_count = standard_suite.countTestCases()
            print(
                f"DEBUG: Standard Django runner would find {standard_count} tests",
                flush=True,
            )

            result = self.run_suite(suite)

            # Output final summary with proper test counts
            total_tests = result.testsRun
            failed_tests = len(result.failures) + len(result.errors)
            skipped_tests = len(result.skipped) if hasattr(result, "skipped") else 0
            passed_tests = total_tests - failed_tests - skipped_tests

            # Debug: Print detailed test counts
            print(f"DEBUG: Test count breakdown:", flush=True)
            print(f"  - total_tests: {total_tests}", flush=True)
            print(f"  - failures: {len(result.failures)}", flush=True)
            print(f"  - errors: {len(result.errors)}", flush=True)
            print(f"  - skipped: {skipped_tests}", flush=True)
            print(f"  - calculated passed: {passed_tests}", flush=True)

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
            print("DEBUG: TEST_SUMMARY output completed", flush=True)

            return len(result.failures) + len(result.errors)

        except Exception as e:
            # Output a summary even if there was an error
            if summary_data is None:
                summary_data = {
                    "run_id": self.run_id,
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
