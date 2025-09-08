"""
Unittest instrumentation for rich telemetry collection
"""

import os
import sys
import argparse
import time
import json
import unittest
from typing import Optional, Dict, Any

from .base_collector import BaseTelemetryCollector


class UnittestInstrumentation(BaseTelemetryCollector):
    """Unittest test instrumentation with rich telemetry collection."""

    def __init__(self):
        super().__init__()

    def run_tests(self, test_args: list = None):
        """Run unittest tests with instrumentation."""
        if test_args is None:
            test_args = []

        # Block network calls
        original_socket = self.block_network_calls()

        try:
            # Create custom test result class
            class InstrumentedTestResult(unittest.TextTestResult):
                def __init__(self, telemetry_collector, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.telemetry_collector = telemetry_collector
                    self.test_start_times = {}

                def startTest(self, test):
                    super().startTest(test)
                    self.test_start_times[test] = time.time()
                    self.telemetry_collector.start_test(test)

                def stopTest(self, test):
                    end_time = time.time()
                    start_time = self.test_start_times.get(test, end_time)
                    duration = (end_time - start_time) * 1000

                    # Determine test status
                    if test in [f[0] for f in self.failures] or test in [
                        e[0] for e in self.errors
                    ]:
                        status = "failed"
                    elif test in [s[0] for s in self.skipped]:
                        status = "skipped"
                    else:
                        status = "passed"

                    # Get test metadata
                    test_id = str(test)
                    test_name = getattr(test, "_testMethodName", "")
                    test_class = test.__class__.__name__
                    test_module = test.__class__.__module__

                    # Try to get test file path
                    test_file = ""
                    if hasattr(test, "__class__") and hasattr(
                        test.__class__, "__module__"
                    ):
                        try:
                            import importlib

                            module = importlib.import_module(test.__class__.__module__)
                            if hasattr(module, "__file__"):
                                test_file = module.__file__
                        except:
                            test_file = f"{test_module}.py"

                    # Create rich telemetry
                    test_telemetry = {
                        "id": test_id,
                        "name": test_name,
                        "class": test_class,
                        "module": test_module,
                        "file": test_file,
                        "line": 0,  # unittest doesn't provide line numbers easily
                        "status": status,
                        "duration": duration,
                        "start_time": start_time,
                        "end_time": end_time,
                        "tags": [],
                        "fixtures": [],
                        "database_queries": {
                            "count": 0,  # unittest doesn't have built-in DB query tracking
                            "total_duration": 0,
                            "slow_queries": [],
                            "duplicate_queries": [],
                        },
                        "http_calls": {
                            "count": len(
                                self.telemetry_collector.network_call_attempts
                            ),
                            "total_duration": 0,
                            "external_calls": self.telemetry_collector.network_call_attempts.copy(),
                        },
                        "performance": {
                            "is_slow": duration > 5000,
                            "is_db_heavy": False,
                            "is_network_heavy": len(
                                self.telemetry_collector.network_call_attempts
                            )
                            > 0,
                            "p95_duration": 0,
                            "p99_duration": 0,
                            "flags": [],
                        },
                        "coverage": {
                            "lines_covered": 0,
                            "lines_total": 0,
                            "coverage_percent": 0.0,
                            "files": [],
                        },
                        "logs": [],
                        "metadata": {
                            "unittest_method": test_name,
                            "unittest_class": test_class,
                            "unittest_module": test_module,
                        },
                    }

                    # Add performance flags
                    if duration > 5000:
                        test_telemetry["performance"]["flags"].append("very_slow")
                    elif duration > 2000:
                        test_telemetry["performance"]["flags"].append("slow")

                    if len(self.telemetry_collector.network_call_attempts) > 0:
                        test_telemetry["performance"]["flags"].append(
                            "network_calls_blocked"
                        )

                    # Add unittest-specific flags
                    if status == "failed":
                        test_telemetry["performance"]["flags"].append("test_failed")
                    elif status == "skipped":
                        test_telemetry["performance"]["flags"].append("test_skipped")

                    self.telemetry_collector.test_results.append(test_telemetry)

                    # Output the test result as JSON
                    print(f"TEST_RESULT:{json.dumps(test_telemetry)}")

                    # Clear network calls for next test
                    self.telemetry_collector.network_call_attempts = []

                    super().stopTest(test)

            # Create custom test runner
            class InstrumentedTestRunner(unittest.TextTestRunner):
                def __init__(self, telemetry_collector, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.telemetry_collector = telemetry_collector

                def run(self, test):
                    result = InstrumentedTestResult(
                        self.telemetry_collector,
                        self.stream,
                        self.descriptions,
                        self.verbosity,
                    )
                    start_time = time.time()
                    startTestRun = getattr(result, "startTestRun", None)
                    if startTestRun is not None:
                        startTestRun()
                    try:
                        test(result)
                    finally:
                        stopTestRun = getattr(result, "stopTestRun", None)
                        if stopTestRun is not None:
                            stopTestRun()
                    stop_time = time.time()
                    time_taken = stop_time - start_time

                    # Output final summary
                    total_tests = result.testsRun
                    passed_tests = (
                        total_tests
                        - len(result.failures)
                        - len(result.errors)
                        - len(result.skipped)
                    )
                    failed_tests = len(result.failures) + len(result.errors)
                    skipped_tests = len(result.skipped)

                    self.telemetry_collector.end_test_run(
                        total_tests, passed_tests, failed_tests, skipped_tests
                    )

                    return result

            # Run tests with instrumentation
            self.start_test_run()

            # Create test suite
            if test_args:
                # If specific test arguments provided, use them
                loader = unittest.TestLoader()
                suite = loader.loadTestsFromNames(test_args)
            else:
                # Discover tests automatically
                loader = unittest.TestLoader()
                suite = loader.discover(".", pattern="test_*.py")

            # Run tests with our custom runner
            runner = InstrumentedTestRunner(self, verbosity=2)
            result = runner.run(suite)

            return 0 if result.wasSuccessful() else 1

        finally:
            self.restore_network_calls(original_socket)


def main():
    """Main entry point for unittest instrumentation."""
    # Get all arguments except the script name
    test_args = sys.argv[1:]

    # Create instrumentation instance
    instrumentation = UnittestInstrumentation()

    # Run tests
    exit_code = instrumentation.run_tests(test_args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
