"""
Base telemetry collector with common functionality
"""

import json
import time
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional


class BaseTelemetryCollector:
    """Base class for telemetry collection across different test frameworks."""

    def __init__(self):
        self.test_results: List[Dict[str, Any]] = []
        self.network_call_attempts: List[Dict[str, Any]] = []
        self.start_time: Optional[float] = None
        self.current_test_start: Optional[float] = None

    def start_test_run(self):
        """Called at the start of a test run."""
        self.start_time = time.time()
        self.test_results = []
        self.network_call_attempts = []

    def start_test(self, test):
        """Called at the start of each test."""
        self.current_test_start = time.time()

    def end_test(self, test, status: str, error: Optional[str] = None):
        """Called at the end of each test."""
        if self.current_test_start is None:
            return

        end_time = time.time()
        duration = (
            end_time - self.current_test_start
        ) * 1000  # Convert to milliseconds

        test_telemetry = {
            "id": str(test),
            "name": str(test),
            "class": getattr(test, "__class__", {}).get("__name__", ""),
            "module": getattr(test, "__class__", {}).get("__module__", ""),
            "file": getattr(test, "_testMethodName", ""),
            "line": 0,
            "status": status,
            "duration": duration,
            "start_time": self.current_test_start,
            "end_time": end_time,
            "tags": [],
            "fixtures": [],
            "database_queries": {
                "count": 0,
                "total_duration": 0,
                "slow_queries": [],
                "duplicate_queries": [],
            },
            "http_calls": {
                "count": len(self.network_call_attempts),
                "total_duration": 0,
                "external_calls": self.network_call_attempts.copy(),
            },
            "performance": {
                "is_slow": duration > 5000,
                "is_db_heavy": False,
                "is_network_heavy": len(self.network_call_attempts) > 0,
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
            test_telemetry["performance"]["flags"].append("very_slow")
        elif duration > 2000:
            test_telemetry["performance"]["flags"].append("slow")

        if len(self.network_call_attempts) > 0:
            test_telemetry["performance"]["flags"].append("network_calls_blocked")

        self.test_results.append(test_telemetry)

        # Output the test result as JSON for the wrapper to capture
        print(f"TEST_RESULT:{json.dumps(test_telemetry)}")

        # Clear network calls for next test
        self.network_call_attempts = []

    def end_test_run(
        self,
        total_tests: int,
        passed_tests: int,
        failed_tests: int,
        skipped_tests: int = 0,
    ):
        """Called at the end of a test run."""
        summary = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "skipped_tests": skipped_tests,
            "exit_code": 0 if failed_tests == 0 else 1,
        }
        print(f"TEST_SUMMARY:{json.dumps(summary)}")

    def record_network_call(self, filename: str, line_number: int, function_name: str):
        """Record a blocked network call attempt."""
        current_thread = threading.current_thread()

        self.network_call_attempts.append(
            {
                "timestamp": datetime.now().isoformat(),
                "file": filename,
                "line": line_number,
                "function": function_name,
                "thread": current_thread.name,
            }
        )

    def block_network_calls(self):
        """Block network calls and record attempts."""
        import socket
        import sys

        original_socket = socket.socket

        def blocked_socket(*args, **kwargs):
            # Get the calling frame to identify where the network call originated
            frame = sys._getframe(1)
            filename = frame.f_code.co_filename
            line_number = frame.f_lineno
            function_name = frame.f_code.co_name

            self.record_network_call(filename, line_number, function_name)

            # Raise an error to prevent the network call
            raise RuntimeError(
                f"Network call blocked in {filename}:{line_number} ({function_name})"
            )

        socket.socket = blocked_socket
        return original_socket

    def restore_network_calls(self, original_socket):
        """Restore original socket functionality."""
        import socket

        socket.socket = original_socket
