"""
Django test runner with minimal telemetry
"""

import json
import sys
import time
import unittest
from datetime import datetime
from django.test.runner import DiscoverRunner
from django.test.utils import CaptureQueriesContext
from django.db import connection, reset_queries
from django.conf import settings
import urllib.request
import urllib.error
import urllib.parse


class TelemetryTestResult(unittest.TextTestResult):
    """Custom test result class for telemetry collection."""

    def __init__(self, run_id, *args, **kwargs):
        # Ensure verbosity is an integer, default to 1 if None
        verbosity = kwargs.get("verbosity", 1)
        if verbosity is None:
            verbosity = 1
        kwargs["verbosity"] = verbosity

        # Ensure stream is not None, default to sys.stdout
        if kwargs.get("stream") is None:
            kwargs["stream"] = sys.stdout

        super().__init__(*args, **kwargs)
        self.run_id = run_id
        self.test_status = {}
        self.test_timings = {}
        self.test_queries = {}  # Store queries for each test
        self.test_network_calls = {}  # Store network calls for each test

        # Enable query logging if not already enabled
        self._ensure_query_logging_enabled()

    def _ensure_query_logging_enabled(self):
        """Ensure Django query logging is enabled."""
        try:
            # Reset any existing queries
            reset_queries()

            # Enable query logging in settings (Django best practice)
            if not getattr(settings, "DEBUG", False):
                settings.DEBUG = True
                print("DEBUG: Enabled DEBUG mode for query logging", flush=True)

            print("DEBUG: Query logging enabled", flush=True)
        except Exception as e:
            print(f"DEBUG: Error enabling query logging: {e}", flush=True)

    def _start_network_monitoring(self, test_id):
        """Start monitoring network calls for a test."""
        try:
            # Store original urllib methods
            self.test_network_calls[test_id] = {
                "calls": [],
                "original_urlopen": urllib.request.urlopen,
                "original_request": getattr(urllib.request, "Request", None),
            }

            # Patch urllib.request.urlopen to track calls
            def tracked_urlopen(*args, **kwargs):
                start_time = time.time()
                url = args[0] if args else kwargs.get("url", "unknown")
                method = "GET"  # Default for urlopen

                try:
                    # Make the actual call
                    result = self.test_network_calls[test_id]["original_urlopen"](
                        *args, **kwargs
                    )
                    duration_ms = round((time.time() - start_time) * 1000)

                    # Log the successful call
                    self.test_network_calls[test_id]["calls"].append(
                        {
                            "url": str(url),
                            "method": method,
                            "duration_ms": duration_ms,
                            "status": "success",
                        }
                    )

                    return result
                except Exception as e:
                    duration_ms = round((time.time() - start_time) * 1000)

                    # Log the failed call
                    self.test_network_calls[test_id]["calls"].append(
                        {
                            "url": str(url),
                            "method": method,
                            "duration_ms": duration_ms,
                            "status": "error",
                            "error": str(e),
                        }
                    )

                    raise

            # Apply the patch
            urllib.request.urlopen = tracked_urlopen

        except Exception as e:
            print(
                f"DEBUG: Error starting network monitoring for {test_id}: {e}",
                flush=True,
            )

    def _stop_network_monitoring(self, test_id):
        """Stop monitoring network calls for a test."""
        try:
            if test_id in self.test_network_calls:
                # Restore original urllib methods
                network_data = self.test_network_calls[test_id]
                if "original_urlopen" in network_data:
                    urllib.request.urlopen = network_data["original_urlopen"]

                # Clean up
                del self.test_network_calls[test_id]
        except Exception as e:
            print(
                f"DEBUG: Error stopping network monitoring for {test_id}: {e}",
                flush=True,
            )

    def startTest(self, test):
        super().startTest(test)
        test_id = str(test)
        self.test_status[test_id] = "running"
        self.test_timings[test_id] = time.time()

        # Reset queries before each test (Django best practice)
        reset_queries()

        # Store initial query count for this test (simpler approach)
        self.test_queries[test_id] = len(connection.queries)

        # Initialize network call tracking for this test
        self.test_network_calls[test_id] = []

        # Start network call monitoring for this test
        self._start_network_monitoring(test_id)

        # Add progress indicator for long-running tests
        if hasattr(self, "_test_count"):
            self._test_count += 1
        else:
            self._test_count = 1

        # Print progress every 50 tests
        if self._test_count % 50 == 0:
            print(f"DEBUG: Progress - {self._test_count} tests started", flush=True)

    def addSuccess(self, test):
        super().addSuccess(test)
        self.test_status[str(test)] = "passed"
        self._output_test_telemetry(test, "passed")

    def addError(self, test, err):
        super().addError(test, err)
        self.test_status[str(test)] = "error"
        self._output_test_telemetry(test, "error")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.test_status[str(test)] = "failed"
        self._output_test_telemetry(test, "failed")

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.test_status[str(test)] = "skipped"
        self._output_test_telemetry(test, "skipped")

    def _output_test_telemetry(self, test, status):
        """Output telemetry for a single test."""
        test_id = str(test)
        end_time = time.time()
        start_time = self.test_timings.get(test_id, end_time)
        duration_ms = round((end_time - start_time) * 1000)

        # Collect database telemetry and clean up
        database_telemetry = self._collect_database_telemetry(test_id)
        self._cleanup_test_queries(test_id)

        # Collect network telemetry and clean up
        network_telemetry = self._collect_network_telemetry(test_id)
        self._stop_network_monitoring(test_id)

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
        print(f"TEST_RESULT:{json.dumps(test_telemetry)}", flush=True)

        # Add completion progress indicator
        if hasattr(self, "_completed_count"):
            self._completed_count += 1
        else:
            self._completed_count = 1

        # Print completion progress every 100 tests
        if self._completed_count % 100 == 0:
            print(
                f"DEBUG: Progress - {self._completed_count} tests completed", flush=True
            )

    def _cleanup_test_queries(self, test_id):
        """Clean up query data for a test."""
        try:
            if test_id in self.test_queries:
                del self.test_queries[test_id]
        except Exception as e:
            print(f"DEBUG: Error cleaning up queries for {test_id}: {e}", flush=True)

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

    def _collect_database_telemetry(self, test_id):
        """Collect database telemetry for a test."""
        try:
            # Get the initial query count for this test
            initial_count = self.test_queries.get(test_id, 0)

            # Check if connection.queries is available
            if not hasattr(connection, "queries"):
                print(
                    f"DEBUG: connection.queries not available for {test_id}", flush=True
                )
                return self._get_empty_database_telemetry()

            current_queries = connection.queries

            # Get queries that were executed during this test
            test_queries = current_queries[initial_count:]
            query_count = len(test_queries)

            # Debug: Show query count for this test
            if query_count > 0:
                print(f"DEBUG: Test {test_id} had {query_count} queries", flush=True)
                # Debug: Show first query structure
                if test_queries:
                    first_query = test_queries[0]
                    print(
                        f"DEBUG: First query keys: {list(first_query.keys())}",
                        flush=True,
                    )
                    print(
                        f"DEBUG: First query time type: {type(first_query.get('time', 'N/A'))}",
                        flush=True,
                    )
            elif initial_count == 0 and len(current_queries) > 0:
                print(
                    f"DEBUG: Test {test_id} - total queries in connection: {len(current_queries)}",
                    flush=True,
                )

            if query_count == 0:
                return self._get_empty_database_telemetry()

            # Analyze queries
            total_duration = 0
            all_queries = []
            query_types = {
                "SELECT": 0,
                "INSERT": 0,
                "UPDATE": 0,
                "DELETE": 0,
                "OTHER": 0,
            }
            query_signatures = {}
            max_duration = 0

            for query in test_queries:
                # Handle both string and numeric duration values
                duration_raw = query.get("time", 0)
                try:
                    duration = float(duration_raw) if duration_raw else 0
                except (ValueError, TypeError):
                    duration = 0

                total_duration += duration
                max_duration = max(max_duration, duration)

                # Store all queries with their details (no judgment calls)
                all_queries.append(
                    {
                        "sql": query.get("sql", "")[:200] + "..."
                        if len(query.get("sql", "")) > 200
                        else query.get("sql", ""),
                        "duration_ms": round(duration * 1000),
                    }
                )

                # Count query types
                sql = query.get("sql", "").upper().strip()
                if sql.startswith("SELECT"):
                    query_types["SELECT"] += 1
                elif sql.startswith("INSERT"):
                    query_types["INSERT"] += 1
                elif sql.startswith("UPDATE"):
                    query_types["UPDATE"] += 1
                elif sql.startswith("DELETE"):
                    query_types["DELETE"] += 1
                else:
                    query_types["OTHER"] += 1

                # Track duplicate queries (same SQL)
                sql_signature = sql[:100]  # First 100 chars for signature
                if sql_signature in query_signatures:
                    query_signatures[sql_signature] += 1
                else:
                    query_signatures[sql_signature] = 1

            # Find duplicate queries
            duplicate_queries = []
            for signature, count in query_signatures.items():
                if count > 1:
                    duplicate_queries.append(
                        {
                            "sql": signature + "..."
                            if len(signature) > 100
                            else signature,
                            "count": count,
                        }
                    )

            # Calculate averages
            avg_duration = (total_duration / query_count) if query_count > 0 else 0

            return {
                "count": query_count,
                "total_duration_ms": round(total_duration * 1000),
                "queries": all_queries,
                "duplicate_queries": duplicate_queries,
                "query_types": query_types,
                "avg_duration_ms": round(avg_duration * 1000),
                "max_duration_ms": round(max_duration * 1000),
            }

        except Exception as e:
            # If there's any error collecting database telemetry, return zeros
            print(
                f"DEBUG: Error collecting database telemetry for {test_id}: {e}",
                flush=True,
            )
            return self._get_empty_database_telemetry()

    def _collect_network_telemetry(self, test_id):
        """Collect network telemetry for a test."""
        try:
            network_data = self.test_network_calls.get(test_id, {})
            calls = network_data.get("calls", [])

            if not calls:
                return {
                    "calls_attempted": 0,
                    "calls_blocked": 0,
                    "total_duration_ms": 0,
                    "external_calls": [],
                    "blocked_calls": [],
                }

            # Analyze network calls
            total_duration = sum(call.get("duration_ms", 0) for call in calls)
            successful_calls = [
                call for call in calls if call.get("status") == "success"
            ]
            failed_calls = [call for call in calls if call.get("status") == "error"]

            return {
                "calls_attempted": len(calls),
                "calls_blocked": 0,  # We don't block, just log
                "total_duration_ms": total_duration,
                "external_calls": successful_calls,
                "blocked_calls": failed_calls,  # Failed calls go here
            }

        except Exception as e:
            print(
                f"DEBUG: Error collecting network telemetry for {test_id}: {e}",
                flush=True,
            )
            return {
                "calls_attempted": 0,
                "calls_blocked": 0,
                "total_duration_ms": 0,
                "external_calls": [],
                "blocked_calls": [],
            }


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
        """Run test suite with per-test telemetry."""
        print(f"DEBUG: Running suite with {suite.countTestCases()} tests", flush=True)

        # Use our custom result class
        result = TelemetryTestResult(
            self.run_id,
            stream=kwargs.get("stream"),
            descriptions=kwargs.get("descriptions"),
            verbosity=kwargs.get("verbosity"),
        )

        # Run the suite
        suite.run(result)

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
