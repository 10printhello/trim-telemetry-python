"""
Base telemetry collection logic shared across test runners
"""

import json
import time
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional


class BaseTelemetryCollector:
    """Base class for telemetry collection across different test frameworks."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.test_status = {}
        self.test_timings = {}
        self.test_queries = {}  # Store queries for each test
        self.test_network_calls = {}  # Store network calls for each test
        self._thread_local = threading.local()

    def start_test(self, test, test_id: str = None):
        """Start tracking a test."""
        if test_id is None:
            test_id = str(test)

        self.test_status[test_id] = "running"
        self.test_timings[test_id] = time.time()

        # Initialize tracking for this test
        self.test_queries[test_id] = 0
        self.test_network_calls[test_id] = []

    def end_test(self, test, status: str, test_id: str = None):
        """End tracking a test and return telemetry data."""
        if test_id is None:
            test_id = str(test)

        end_time = time.time()
        start_time = self.test_timings.get(test_id, end_time)
        duration_ms = round((end_time - start_time) * 1000)

        # Collect telemetry data
        database_telemetry = self._collect_database_telemetry(test_id)
        network_telemetry = self._collect_network_telemetry(test_id)

        # Create test telemetry
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
            "database": database_telemetry,
            "network": network_telemetry,
            "test_performance": {
                "duration_ms": duration_ms,
            },
        }

        # Clean up test data
        self._cleanup_test_data(test_id)

        return test_telemetry

    def _cleanup_test_data(self, test_id: str):
        """Clean up test tracking data."""
        try:
            if test_id in self.test_queries:
                del self.test_queries[test_id]
            if test_id in self.test_network_calls:
                del self.test_network_calls[test_id]
            if test_id in self.test_timings:
                del self.test_timings[test_id]
            if test_id in self.test_status:
                del self.test_status[test_id]
        except Exception:
            # Silently handle errors - telemetry should not break tests
            pass

    def _get_empty_database_telemetry(self):
        """Return empty database telemetry structure."""
        return {
            "count": 0,
            "total_duration_ms": 0,
            "queries": [],
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
        }

    def _collect_database_telemetry(self, test_id: str):
        """Collect database telemetry for a test. Override in subclasses."""
        # Default implementation returns empty telemetry
        # Django runner will override this with actual database query collection
        return self._get_empty_database_telemetry()

    def _collect_network_telemetry(self, test_id: str):
        """Collect network telemetry for a test. Override in subclasses."""
        try:
            network_data = self.test_network_calls.get(test_id, {})
            calls = network_data.get("calls", [])

            if not calls:
                return {
                    "total_calls": 0,
                    "urls": [],
                }

            return {
                "total_calls": len(calls),
                "urls": [call.get("url", "unknown") for call in calls],
            }

        except Exception:
            return {
                "total_calls": 0,
                "urls": [],
            }

    def start_network_monitoring(self, test_id: str):
        """Start monitoring network calls for a test. Override in subclasses."""
        # Default implementation does nothing
        # Subclasses can override to implement actual network monitoring
        pass

    def stop_network_monitoring(self, test_id: str):
        """Stop monitoring network calls for a test. Override in subclasses."""
        # Default implementation does nothing
        # Subclasses can override to implement actual network monitoring
        pass

    def output_test_telemetry(self, test_telemetry: Dict[str, Any]):
        """Output test telemetry in the standard format."""
        print(f"TEST_RESULT:{json.dumps(test_telemetry)}", flush=True)

    def output_test_summary(
        self,
        total_tests: int,
        passed_tests: int,
        failed_tests: int,
        skipped_tests: int = 0,
    ):
        """Output test run summary."""
        summary_data = {
            "run_id": self.run_id,
            "type": "test_run_summary",
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "skipped_tests": skipped_tests,
            "exit_code": 0 if failed_tests == 0 else 1,
        }
        print(f"TEST_SUMMARY:{json.dumps(summary_data)}", flush=True)
