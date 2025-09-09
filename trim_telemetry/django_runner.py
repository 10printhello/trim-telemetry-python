"""
Django test runner with minimal telemetry
"""

import json
import time
import unittest
from datetime import datetime
from django.test.runner import DiscoverRunner


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

        # Create custom test result class for telemetry
        class TelemetryTestResult(unittest.TextTestResult):
            def __init__(self, run_id, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.run_id = run_id
                self.test_status = {}
                self.test_timings = {}

            def startTest(self, test):
                super().startTest(test)
                self.test_status[str(test)] = "running"
                self.test_timings[str(test)] = time.time()

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
                    "database": {
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
                    },
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
