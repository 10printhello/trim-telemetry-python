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
