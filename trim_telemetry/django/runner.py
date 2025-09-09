"""
Django test runner with telemetry collection
"""

import sys
import unittest
from datetime import datetime
from django.test.runner import DiscoverRunner
from .telemetry import DjangoTelemetryCollector


class TelemetryTestResult(unittest.TextTestResult):
    """Custom test result class for Django telemetry collection."""

    def __init__(self, telemetry_collector, *args, **kwargs):
        # Ensure verbosity is an integer, default to 1 if None
        verbosity = kwargs.get("verbosity", 1)
        if verbosity is None:
            verbosity = 1
        kwargs["verbosity"] = verbosity

        # Ensure stream is not None, default to sys.stdout
        if kwargs.get("stream") is None:
            kwargs["stream"] = sys.stdout

        super().__init__(*args, **kwargs)
        self.telemetry_collector = telemetry_collector

    def startTest(self, test):
        super().startTest(test)
        self.telemetry_collector.start_test(test)

    def addSuccess(self, test):
        super().addSuccess(test)
        test_telemetry = self.telemetry_collector.end_test(test, "passed")
        self.telemetry_collector.output_test_telemetry(test_telemetry)

    def addError(self, test, err):
        super().addError(test, err)
        test_telemetry = self.telemetry_collector.end_test(test, "error")
        self.telemetry_collector.output_test_telemetry(test_telemetry)

    def addFailure(self, test, err):
        super().addFailure(test, err)
        test_telemetry = self.telemetry_collector.end_test(test, "failed")
        self.telemetry_collector.output_test_telemetry(test_telemetry)

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        test_telemetry = self.telemetry_collector.end_test(test, "skipped")
        self.telemetry_collector.output_test_telemetry(test_telemetry)


class TelemetryTestRunner(DiscoverRunner):
    """Django test runner with telemetry collection."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.telemetry_collector = DjangoTelemetryCollector(self.run_id)

    def run_suite(self, suite, **kwargs):
        """Run test suite with per-test telemetry."""
        # Use our custom result class
        result = TelemetryTestResult(
            self.telemetry_collector,
            stream=kwargs.get("stream"),
            descriptions=kwargs.get("descriptions"),
            verbosity=kwargs.get("verbosity"),
        )

        # Run the suite
        suite.run(result)

        return result

    def run_tests(self, test_labels=None, **kwargs):
        """Run tests with telemetry."""
        # Use standard Django behavior
        result = super().run_tests(test_labels, **kwargs)

        # Output basic summary
        if hasattr(result, "testsRun"):
            total_tests = result.testsRun
            failed_tests = len(result.failures) + len(result.errors)
            skipped_tests = len(result.skipped) if hasattr(result, "skipped") else 0
            passed_tests = total_tests - failed_tests - skipped_tests

            self.telemetry_collector.output_test_summary(
                total_tests, passed_tests, failed_tests, skipped_tests
            )

        return result


def main():
    """Main entry point for Django telemetry runner."""
    import os
    import django

    # Set up Django environment
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    django.setup()

    # Get all arguments except the script name
    test_args = sys.argv[1:]

    # Create test runner
    runner = TelemetryTestRunner()

    # Run tests
    result = runner.run_tests(test_args)

    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
