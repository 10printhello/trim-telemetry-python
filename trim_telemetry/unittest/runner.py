"""
Unittest test runner with telemetry collection
"""

import sys
import unittest
from datetime import datetime
from ..base_telemetry import BaseTelemetryCollector


class UnittestTelemetryCollector(BaseTelemetryCollector):
    """Unittest-specific telemetry collector."""

    def __init__(self, run_id: str):
        super().__init__(run_id)
        self.test_start_times = {}

    def start_test(self, test, test_id: str = None):
        """Start tracking a unittest test."""
        if test_id is None:
            test_id = str(test)

        super().start_test(test, test_id)
        self.test_start_times[test_id] = datetime.now().timestamp()


class TelemetryTestResult(unittest.TextTestResult):
    """Custom test result class for unittest telemetry collection."""

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

    def stopTest(self, test):
        end_time = datetime.now().timestamp()
        test_id = str(test)
        start_time = self.telemetry_collector.test_start_times.get(test_id, end_time)
        duration_ms = round((end_time - start_time) * 1000)

        # Determine test status
        if test in [f[0] for f in self.failures] or test in [e[0] for e in self.errors]:
            status = "failed"
        elif test in [s[0] for s in self.skipped]:
            status = "skipped"
        else:
            status = "passed"

        # Get test metadata
        test_name = getattr(test, "_testMethodName", "")
        test_class = test.__class__.__name__
        test_module = test.__class__.__module__

        # Try to get test file path
        test_file = ""
        if hasattr(test, "__class__") and hasattr(test.__class__, "__module__"):
            try:
                import importlib

                module = importlib.import_module(test.__class__.__module__)
                if hasattr(module, "__file__"):
                    test_file = module.__file__
            except Exception:
                test_file = f"{test_module}.py"

        # Create test telemetry
        test_telemetry = {
            "run_id": self.telemetry_collector.run_id,
            "id": test_id,
            "name": test_name,
            "class": test_class,
            "module": test_module,
            "file": test_file,
            "line": 0,  # unittest doesn't provide line numbers easily
            "status": status,
            "duration_ms": duration_ms,
            "start_time": datetime.fromtimestamp(start_time).isoformat(),
            "end_time": datetime.fromtimestamp(end_time).isoformat(),
            "database": self.telemetry_collector._get_empty_database_telemetry(),
            "network": self.telemetry_collector._collect_network_telemetry(test_id),
            "test_performance": {
                "duration_ms": duration_ms,
            },
        }

        self.telemetry_collector.output_test_telemetry(test_telemetry)
        super().stopTest(test)


class TelemetryTestRunner(unittest.TextTestRunner):
    """Unittest test runner with telemetry collection."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.telemetry_collector = UnittestTelemetryCollector(self.run_id)

    def run(self, test):
        result = TelemetryTestResult(
            self.telemetry_collector,
            self.stream,
            self.descriptions,
            self.verbosity,
        )

        start_time = datetime.now().timestamp()
        startTestRun = getattr(result, "startTestRun", None)
        if startTestRun is not None:
            startTestRun()

        try:
            test(result)
        finally:
            stopTestRun = getattr(result, "stopTestRun", None)
            if stopTestRun is not None:
                stopTestRun()

        stop_time = datetime.now().timestamp()

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

        self.telemetry_collector.output_test_summary(
            total_tests, passed_tests, failed_tests, skipped_tests
        )

        return result


def main():
    """Main entry point for unittest telemetry runner."""
    # Get all arguments except the script name
    test_args = sys.argv[1:]

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
    runner = TelemetryTestRunner(verbosity=2)
    result = runner.run(suite)

    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
