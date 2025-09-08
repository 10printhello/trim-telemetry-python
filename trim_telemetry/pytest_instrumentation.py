"""
Pytest instrumentation for rich telemetry collection
"""

import os
import sys
import argparse
import time
import json
from typing import Optional, Dict, Any

from .base_collector import BaseTelemetryCollector


class PytestInstrumentation(BaseTelemetryCollector):
    """Pytest test instrumentation with rich telemetry collection."""

    def __init__(self):
        super().__init__()

    def run_tests(self, test_args: list = None):
        """Run pytest tests with instrumentation."""
        if test_args is None:
            test_args = []

        # Block network calls
        original_socket = self.block_network_calls()

        try:
            # Import pytest
            import pytest
            from _pytest.config import Config
            from _pytest.main import Session
            from _pytest.reports import TestReport
            from _pytest.runner import CallInfo

            # Create custom pytest plugin
            class TelemetryPlugin:
                def __init__(self, telemetry_collector):
                    self.telemetry_collector = telemetry_collector
                    self.test_start_times = {}

                def pytest_runtest_setup(self, item):
                    """Called before each test setup."""
                    self.test_start_times[item.nodeid] = time.time()
                    self.telemetry_collector.start_test(item)

                def pytest_runtest_teardown(self, item):
                    """Called after each test teardown."""
                    pass

                def pytest_runtest_logreport(self, report: TestReport):
                    """Called for each test report."""
                    if report.when == "call":  # Only process the actual test call
                        test_id = report.nodeid
                        start_time = self.test_start_times.get(test_id, time.time())
                        end_time = time.time()
                        duration = (end_time - start_time) * 1000

                        # Determine test status
                        if report.outcome == "passed":
                            status = "passed"
                        elif report.outcome == "failed":
                            status = "failed"
                        elif report.outcome == "skipped":
                            status = "skipped"
                        else:
                            status = "unknown"

                        # Get test metadata
                        test_name = (
                            report.nodeid.split("::")[-1]
                            if "::" in report.nodeid
                            else report.nodeid
                        )
                        test_file = (
                            report.nodeid.split("::")[0]
                            if "::" in report.nodeid
                            else ""
                        )
                        test_class = ""
                        if "::" in report.nodeid and len(report.nodeid.split("::")) > 2:
                            test_class = report.nodeid.split("::")[1]

                        # Create rich telemetry
                        test_telemetry = {
                            "id": test_id,
                            "name": test_name,
                            "class": test_class,
                            "module": test_file.replace(".py", "").replace("/", "."),
                            "file": test_file,
                            "line": getattr(report, "lineno", 0),
                            "status": status,
                            "duration": duration,
                            "start_time": start_time,
                            "end_time": end_time,
                            "tags": [],
                            "fixtures": [],
                            "database_queries": {
                                "count": 0,  # Pytest doesn't have built-in DB query tracking
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
                                "pytest_outcome": report.outcome,
                                "pytest_when": report.when,
                                "pytest_sections": [
                                    section[0] for section in report.sections
                                ]
                                if hasattr(report, "sections")
                                else [],
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

                        # Add pytest-specific flags
                        if report.outcome == "failed":
                            test_telemetry["performance"]["flags"].append("test_failed")
                        elif report.outcome == "skipped":
                            test_telemetry["performance"]["flags"].append(
                                "test_skipped"
                            )

                        self.telemetry_collector.test_results.append(test_telemetry)

                        # Output the test result as JSON
                        print(f"TEST_RESULT:{json.dumps(test_telemetry)}")

                        # Clear network calls for next test
                        self.telemetry_collector.network_call_attempts = []

                def pytest_sessionfinish(self, session: Session, exitstatus: int):
                    """Called after test session finishes."""
                    # Count test results
                    total_tests = len(self.telemetry_collector.test_results)
                    passed_tests = len(
                        [
                            r
                            for r in self.telemetry_collector.test_results
                            if r["status"] == "passed"
                        ]
                    )
                    failed_tests = len(
                        [
                            r
                            for r in self.telemetry_collector.test_results
                            if r["status"] == "failed"
                        ]
                    )
                    skipped_tests = len(
                        [
                            r
                            for r in self.telemetry_collector.test_results
                            if r["status"] == "skipped"
                        ]
                    )

                    self.telemetry_collector.end_test_run(
                        total_tests, passed_tests, failed_tests, skipped_tests
                    )

            # Run tests with instrumentation
            self.start_test_run()

            # Create and register the plugin
            plugin = TelemetryPlugin(self)

            # Run pytest with our plugin
            exit_code = pytest.main(
                test_args
                + ["-p", "no:cacheprovider"],  # Disable cache to avoid conflicts
                plugins=[plugin],
            )

            return exit_code

        except ImportError:
            print(
                "ERROR: pytest is not installed. Please install it with: pip install pytest"
            )
            return 1
        finally:
            self.restore_network_calls(original_socket)


def main():
    """Main entry point for pytest instrumentation."""
    # Get all arguments except the script name
    test_args = sys.argv[1:]

    # Create instrumentation instance
    instrumentation = PytestInstrumentation()

    # Run tests
    exit_code = instrumentation.run_tests(test_args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
