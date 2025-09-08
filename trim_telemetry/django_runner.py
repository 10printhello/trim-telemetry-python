"""
Django test runner with rich telemetry collection
"""

import json
import time
import unittest
from datetime import datetime
from django.test.runner import DiscoverRunner
from django.test.utils import CaptureQueriesContext
from django.db import connection
from .base_collector import BaseTelemetryCollector


class TrimTelemetryRunner(DiscoverRunner):
    """Django test runner with rich telemetry collection."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.telemetry_collector = BaseTelemetryCollector()
        # Block network calls
        self.original_socket = self.telemetry_collector.block_network_calls()

    def run_suite(self, suite, **kwargs):
        """Run test suite with instrumentation."""

        class InstrumentedTestResult(unittest.TextTestResult):
            def __init__(self, telemetry_collector, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.telemetry_collector = telemetry_collector
                self.test_status = {}

            def startTest(self, test):
                super().startTest(test)
                self.telemetry_collector.start_test(test)

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
                # Get database query info
                queries = len(connection.queries)
                query_time = sum(float(q["time"]) for q in connection.queries)

                # Get test timing
                if self.telemetry_collector.current_test_start:
                    end_time = time.time()
                    start_time = self.telemetry_collector.current_test_start
                    duration = (end_time - start_time) * 1000  # Convert to milliseconds

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
                        "database_queries": {
                            "count": queries,
                            "total_duration": round(
                                query_time * 1000
                            ),  # Convert to milliseconds
                            "slow_queries": [
                                {
                                    "sql": q["sql"],
                                    "time": float(q["time"]),
                                    "duration": round(float(q["time"]) * 1000),
                                }
                                for q in connection.queries
                                if float(q["time"]) > 0.1  # Slow queries > 100ms
                            ],
                            "duplicate_queries": [],
                        },
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
                            "p95_duration": round(duration),
                            "p99_duration": round(duration),
                            "flags": [],
                        },
                        "coverage": {
                            "lines_covered": 0,
                            "lines_total": 0,
                            "coverage_percent": 0.0,
                            "files": [],
                        },
                        "logs": [],
                        "metadata": {},
                    }

                    # Add performance flags
                    if duration > 5000:
                        test_telemetry["performance"]["flags"].append("very_slow")
                    elif duration > 1000:
                        test_telemetry["performance"]["flags"].append("slow")

                    if queries > 100:
                        test_telemetry["performance"]["flags"].append("high_db_queries")
                    elif queries > 50:
                        test_telemetry["performance"]["flags"].append(
                            "moderate_db_queries"
                        )

                    if len(self.telemetry_collector.network_call_attempts) > 0:
                        test_telemetry["performance"]["flags"].append(
                            "network_calls_blocked"
                        )

                    # Output telemetry data
                    print(f"TEST_RESULT:{json.dumps(test_telemetry)}")

                    # Clear network calls for next test
                    self.telemetry_collector.network_call_attempts = []

                super().stopTest(test)

        # Create test runner with instrumentation
        runner = unittest.TextTestRunner(
            verbosity=self.verbosity,
            resultclass=lambda *args, **kwargs: InstrumentedTestResult(
                self.telemetry_collector, *args, **kwargs
            ),
        )

        return runner.run(suite)

    def run_tests(self, test_labels=None, **kwargs):
        """Run tests with telemetry collection."""
        self.telemetry_collector.start_test_run()

        try:
            # Run tests with instrumentation
            result = super().run_tests(test_labels, **kwargs)

            # Output final summary - result is an integer (number of failures)
            # We need to get the actual test result from the suite run
            summary = {
                "total_tests": 0,  # Will be updated by individual test results
                "passed_tests": 0,
                "failed_tests": result,  # result is the number of failures
                "skipped_tests": 0,
                "exit_code": 0 if result == 0 else 1,
            }
            print(f"TEST_SUMMARY:{json.dumps(summary)}")

            return result

        finally:
            # Restore network calls
            self.telemetry_collector.restore_network_calls(self.original_socket)
