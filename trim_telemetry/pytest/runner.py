"""
Pytest test runner with telemetry collection
"""

import sys
from datetime import datetime
from ..base_telemetry import BaseTelemetryCollector


class PytestTelemetryCollector(BaseTelemetryCollector):
    """Pytest-specific telemetry collector."""

    def __init__(self, run_id: str):
        super().__init__(run_id)
        self.test_start_times = {}

    def start_test(self, test, test_id: str = None):
        """Start tracking a pytest test."""
        if test_id is None:
            test_id = test.nodeid if hasattr(test, "nodeid") else str(test)

        super().start_test(test, test_id)
        self.test_start_times[test_id] = datetime.now().timestamp()

    def end_test(self, test, status: str, test_id: str = None):
        """End tracking a pytest test and return telemetry data."""
        if test_id is None:
            test_id = test.nodeid if hasattr(test, "nodeid") else str(test)

        return super().end_test(test, status, test_id)


class PytestTelemetryPlugin:
    """Pytest plugin for telemetry collection."""

    def __init__(self, telemetry_collector):
        self.telemetry_collector = telemetry_collector

    def pytest_runtest_setup(self, item):
        """Called before each test setup."""
        self.telemetry_collector.start_test(item)

    def pytest_runtest_logreport(self, report):
        """Called for each test report."""
        if report.when == "call":  # Only process the actual test call
            test_id = report.nodeid
            start_time = self.telemetry_collector.test_start_times.get(
                test_id, datetime.now().timestamp()
            )
            end_time = datetime.now().timestamp()
            duration_ms = round((end_time - start_time) * 1000)

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
            test_file = report.nodeid.split("::")[0] if "::" in report.nodeid else ""
            test_class = ""
            if "::" in report.nodeid and len(report.nodeid.split("::")) > 2:
                test_class = report.nodeid.split("::")[1]

            # Create test telemetry
            test_telemetry = {
                "run_id": self.telemetry_collector.run_id,
                "id": test_id,
                "name": test_name,
                "class": test_class,
                "module": test_file.replace(".py", "").replace("/", "."),
                "file": test_file,
                "line": getattr(report, "lineno", 0),
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

    def pytest_sessionfinish(self, session, exitstatus):
        """Called after test session finishes."""
        # Summary data is now calculated by analysis tools from individual test records
        pass


def main():
    """Main entry point for pytest telemetry runner."""
    try:
        import pytest
    except ImportError:
        print(
            "ERROR: pytest is not installed. Please install it with: pip install pytest"
        )
        sys.exit(1)

    # Get all arguments except the script name
    test_args = sys.argv[1:]

    # Create telemetry collector
    run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    telemetry_collector = PytestTelemetryCollector(run_id)

    # Create and register the plugin
    plugin = PytestTelemetryPlugin(telemetry_collector)

    # Run pytest with our plugin
    exit_code = pytest.main(
        test_args + ["-p", "no:cacheprovider"],  # Disable cache to avoid conflicts
        plugins=[plugin],
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
