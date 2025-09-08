"""
Django test instrumentation for rich telemetry collection
"""

import os
import sys
import time
import argparse
from typing import Optional

from .base_collector import BaseTelemetryCollector


class DjangoInstrumentation(BaseTelemetryCollector):
    """Django test instrumentation with rich telemetry collection."""

    def __init__(self, settings_module: str = "core.settings"):
        super().__init__()
        self.settings_module = settings_module

    def setup_django(self):
        """Set up Django environment."""
        # Add current directory to Python path
        project_root = os.path.abspath(".")
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        # Set Django settings
        os.environ.setdefault("DJANGO_SETTINGS_MODULE", self.settings_module)

        import django

        django.setup()

        from django.test.runner import DiscoverRunner
        from django.test.utils import CaptureQueriesContext
        from django.db import connection
        from django.conf import settings

        return DiscoverRunner, CaptureQueriesContext, connection, settings

    def run_tests(self, test_args: list = None):
        """Run Django tests with instrumentation."""
        if test_args is None:
            test_args = []

        # Set up Django
        DiscoverRunner, CaptureQueriesContext, connection, settings = (
            self.setup_django()
        )

        # Block network calls
        original_socket = self.block_network_calls()

        try:
            # Create custom test runner
            class InstrumentedTestRunner(DiscoverRunner):
                def __init__(self, telemetry_collector, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.telemetry_collector = telemetry_collector

                def run_suite(self, suite, **kwargs):
                    import unittest

                    class InstrumentedTestResult(unittest.TextTestResult):
                        def __init__(self, telemetry_collector, *args, **kwargs):
                            super().__init__(*args, **kwargs)
                            self.telemetry_collector = telemetry_collector

                        def startTest(self, test):
                            super().startTest(test)
                            self.telemetry_collector.start_test(test)

                        def stopTest(self, test):
                            # Get database query info
                            queries = len(connection.queries)
                            query_time = sum(
                                float(q["time"]) for q in connection.queries
                            )

                            # Determine test status
                            if test in [f[0] for f in self.failures] or test in [
                                e[0] for e in self.errors
                            ]:
                                status = "failed"
                            else:
                                status = "passed"

                            # Create enhanced test telemetry
                            if self.telemetry_collector.current_test_start:
                                end_time = time.time()
                                duration = (
                                    end_time
                                    - self.telemetry_collector.current_test_start
                                ) * 1000

                                test_telemetry = {
                                    "id": str(test),
                                    "name": str(test),
                                    "class": test.__class__.__name__,
                                    "module": test.__class__.__module__,
                                    "file": getattr(test, "_testMethodName", ""),
                                    "line": 0,
                                    "status": status,
                                    "duration": duration,
                                    "start_time": self.telemetry_collector.current_test_start,
                                    "end_time": end_time,
                                    "tags": [],
                                    "fixtures": [],
                                    "database_queries": {
                                        "count": queries,
                                        "total_duration": query_time,
                                        "slow_queries": [
                                            q
                                            for q in connection.queries
                                            if float(q["time"]) > 1.0
                                        ],
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
                                        "is_db_heavy": queries > 50,
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
                                    "metadata": {},
                                }

                                # Add performance flags
                                if duration > 5000:
                                    test_telemetry["performance"]["flags"].append(
                                        "very_slow"
                                    )
                                elif duration > 2000:
                                    test_telemetry["performance"]["flags"].append(
                                        "slow"
                                    )

                                if queries > 100:
                                    test_telemetry["performance"]["flags"].append(
                                        "high_db_queries"
                                    )
                                elif queries > 50:
                                    test_telemetry["performance"]["flags"].append(
                                        "moderate_db_queries"
                                    )

                                if (
                                    len(self.telemetry_collector.network_call_attempts)
                                    > 0
                                ):
                                    test_telemetry["performance"]["flags"].append(
                                        "network_calls_blocked"
                                    )

                                self.telemetry_collector.test_results.append(
                                    test_telemetry
                                )

                                # Output the test result as JSON
                                import json

                                print(f"TEST_RESULT:{json.dumps(test_telemetry)}")

                                # Clear network calls for next test
                                self.telemetry_collector.network_call_attempts = []

                            super().stopTest(test)

                    runner = unittest.TextTestRunner(
                        verbosity=2,
                        resultclass=lambda *args, **kwargs: InstrumentedTestResult(
                            self.telemetry_collector, *args, **kwargs
                        ),
                    )
                    return runner.run(suite)

            # Run tests with instrumentation
            self.start_test_run()

            runner = InstrumentedTestRunner(self)
            result = runner.run_tests(test_args)

            # Output final summary
            total_tests = result.testsRun
            passed_tests = total_tests - len(result.failures) - len(result.errors)
            failed_tests = len(result.failures) + len(result.errors)
            skipped_tests = len(result.skipped) if hasattr(result, "skipped") else 0

            self.end_test_run(total_tests, passed_tests, failed_tests, skipped_tests)

            return 0 if result.wasSuccessful() else 1

        finally:
            self.restore_network_calls(original_socket)


def main():
    """Main entry point for Django instrumentation."""
    parser = argparse.ArgumentParser(
        description="Django test instrumentation with rich telemetry"
    )
    parser.add_argument(
        "--settings", default="core.settings", help="Django settings module"
    )
    parser.add_argument(
        "test_args", nargs="*", help="Test arguments to pass to Django test runner"
    )

    args = parser.parse_args()

    # Create instrumentation instance
    instrumentation = DjangoInstrumentation(settings_module=args.settings)

    # Run tests
    exit_code = instrumentation.run_tests(args.test_args)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
