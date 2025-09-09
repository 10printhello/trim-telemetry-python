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
        """Run test suite with minimal telemetry."""
        print(f"DEBUG: Running suite with {suite.countTestCases()} tests", flush=True)

        # Use standard Django behavior but add minimal test result tracking
        result = super().run_suite(suite, **kwargs)

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
