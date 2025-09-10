"""
Base telemetry collection logic shared across test runners
"""

import json
import time
import threading
import os
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

        # Set up telemetry file
        self.telemetry_dir = os.path.join(os.getcwd(), ".telemetry")
        self.telemetry_file = os.path.join(self.telemetry_dir, f"{run_id}.ndjson")
        self._ensure_telemetry_file()

    def _ensure_telemetry_file(self):
        """Ensure the telemetry directory and file exist and are writable."""
        try:
            # Create the .telemetry directory if it doesn't exist
            if not os.path.exists(self.telemetry_dir):
                os.makedirs(self.telemetry_dir, exist_ok=True)

            # Create the file if it doesn't exist
            if not os.path.exists(self.telemetry_file):
                with open(self.telemetry_file, "w") as f:
                    pass  # Create empty file
        except Exception:
            # If we can't create the file, fall back to stdout
            self.telemetry_file = None

    def _write_telemetry(self, data: Dict[str, Any]):
        """Write telemetry data to file or stdout."""
        try:
            if self.telemetry_file:
                with open(self.telemetry_file, "a") as f:
                    f.write(json.dumps(data) + "\n")
                    f.flush()
            else:
                # Fallback to stdout if file writing fails
                print(json.dumps(data), flush=True)
        except Exception:
            # If file writing fails, fall back to stdout
            print(json.dumps(data), flush=True)

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

        # Create test telemetry with flattened database fields
        test_telemetry = {
            "run_id": self.run_id,
            "id": test_id,
            "name": getattr(test, "_testMethodName", test_id),
            "class": test.__class__.__name__,
            "module": test.__class__.__module__,
            "file": test.__class__.__module__.replace(".", "/") + ".py",
            "line": 0,
            "status": status,
            "test_duration_ms": duration_ms,
            "start_time": datetime.fromtimestamp(start_time).isoformat(),
            "end_time": datetime.fromtimestamp(end_time).isoformat(),
            "db_count": database_telemetry.get("count", 0),
            "db_total_duration_ms": database_telemetry.get("total_duration_ms", 0),
            "db_queries": database_telemetry.get("queries", []),
            "db_duplicate_queries": database_telemetry.get("duplicate_queries", []),
            "db_select_count": database_telemetry.get("query_types", {}).get(
                "SELECT", 0
            ),
            "db_insert_count": database_telemetry.get("query_types", {}).get(
                "INSERT", 0
            ),
            "db_update_count": database_telemetry.get("query_types", {}).get(
                "UPDATE", 0
            ),
            "db_delete_count": database_telemetry.get("query_types", {}).get(
                "DELETE", 0
            ),
            "db_other_count": database_telemetry.get("query_types", {}).get("OTHER", 0),
            "db_avg_duration_ms": database_telemetry.get("avg_duration_ms", 0),
            "db_max_duration_ms": database_telemetry.get("max_duration_ms", 0),
            "net_total_calls": network_telemetry.get("total_calls", 0),
            "net_urls": network_telemetry.get("urls", []),
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
        """Output test telemetry to .telemetry file."""
        self._write_telemetry(test_telemetry)

    def output_test_summary(
        self,
        total_tests: int,
        passed_tests: int,
        failed_tests: int,
        skipped_tests: int = 0,
    ):
        """Output test run summary to .telemetry file."""
        summary_data = {
            "run_id": self.run_id,
            "type": "test_run_summary",
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "skipped_tests": skipped_tests,
            "exit_code": 0 if failed_tests == 0 else 1,
        }
        self._write_telemetry(summary_data)
