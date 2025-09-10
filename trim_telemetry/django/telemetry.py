"""
Django-specific telemetry collection
"""

import urllib.request
from django.db import connection, reset_queries
from ..base_telemetry import BaseTelemetryCollector


class DjangoTelemetryCollector(BaseTelemetryCollector):
    """Django-specific telemetry collector with database and network monitoring."""

    def __init__(self, run_id: str):
        super().__init__(run_id)
        self._ensure_query_logging_enabled()

    def _ensure_query_logging_enabled(self):
        """Ensure Django query logging is enabled."""
        try:
            # Reset any existing queries
            reset_queries()

            # Note: Django's test runner already enables query logging for tests
            # We don't need to modify settings.DEBUG as it can interfere with
            # database setup/teardown behavior
        except Exception:
            # Silently handle errors - telemetry should not break tests
            pass

    def start_test(self, test, test_id: str = None):
        """Start tracking a Django test with database and network monitoring."""
        super().start_test(test, test_id)

        if test_id is None:
            test_id = str(test)

        # Store initial query count for this test BEFORE resetting
        initial_count = len(connection.queries)
        self.test_queries[test_id] = initial_count
        
        # Start network monitoring
        self.start_network_monitoring(test_id)

        # Reset queries after storing initial count (Django best practice)
        reset_queries()

    def end_test(self, test, status: str, test_id: str = None):
        """End tracking a Django test and stop network monitoring."""
        if test_id is None:
            test_id = str(test)
            
        # Call parent end_test method first to collect data
        result = super().end_test(test, status, test_id)
        
        # Stop network monitoring after data collection
        self.stop_network_monitoring(test_id)
        
        return result

    def _collect_database_telemetry(self, test_id: str):
        """Collect database telemetry for a Django test."""
        try:
            # Get the initial query count for this test
            initial_count = self.test_queries.get(test_id, 0)

            # Check if connection.queries is available
            if not hasattr(connection, "queries"):
                return self._get_empty_database_telemetry()

            current_queries = connection.queries

            # Get queries that were executed during this test
            test_queries = current_queries[initial_count:]
            query_count = len(test_queries)

            if query_count == 0:
                return self._get_empty_database_telemetry()

            # Analyze queries
            total_duration = 0
            query_signatures = {}

            # First pass: collect all queries and track signatures
            for query in test_queries:
                # Handle both string and numeric duration values
                duration_raw = query.get("time", 0)
                try:
                    duration = float(duration_raw) if duration_raw else 0
                except (ValueError, TypeError):
                    duration = 0

                total_duration += duration

                # Track duplicate queries (same SQL)
                sql = query.get("sql", "").upper().strip()
                sql_signature = sql[:100]  # First 100 chars for signature
                if sql_signature in query_signatures:
                    query_signatures[sql_signature]["count"] += 1
                    query_signatures[sql_signature]["total_duration"] += duration
                else:
                    query_signatures[sql_signature] = {
                        "sql": query.get("sql", "")[:200] + "..."
                        if len(query.get("sql", "")) > 200
                        else query.get("sql", ""),
                        "count": 1,
                        "total_duration": duration,
                    }

            # Second pass: create query objects with counts
            all_queries = []
            for signature, data in query_signatures.items():
                all_queries.append({
                    "sql": data["sql"],
                    "total_duration_ms": round(data["total_duration"] * 1000),
                    "count": data["count"],
                })

            return {
                "queries": all_queries,
            }

        except Exception:
            # If there's any error collecting database telemetry, return zeros
            return self._get_empty_database_telemetry()

    def start_network_monitoring(self, test_id: str):
        """Start monitoring network calls for a Django test."""
        try:
            # Store original urllib methods and initialize call tracking
            self.test_network_calls[test_id] = {
                "calls": [],
            }

            # Only patch if not already patched
            if not hasattr(urllib.request, '_trim_telemetry_patched'):
                # Store the original function globally
                urllib.request._original_urlopen = urllib.request.urlopen
                urllib.request._trim_telemetry_patched = True

            # Create a simple tracked version that just logs URLs
            def tracked_urlopen(*args, **kwargs):
                # Just capture the URL - no timing, no blocking
                url = args[0] if args else kwargs.get("url", "unknown")
                url_str = str(url)

                # Make the actual call using the original function (no timing)
                result = urllib.request._original_urlopen(*args, **kwargs)

                # Log the call for all active tests
                for active_test_id, data in self.test_network_calls.items():
                    if data is not None:  # Check if test is still active
                        data["calls"].append({"url": url_str})

                return result

            # Apply the patch
            urllib.request.urlopen = tracked_urlopen

        except Exception:
            # Silently handle errors - telemetry should not break tests
            pass

    def stop_network_monitoring(self, test_id: str):
        """Stop monitoring network calls for a Django test."""
        try:
            if test_id in self.test_network_calls:
                # Mark test as inactive by setting to None
                self.test_network_calls[test_id] = None
                
                # If no active tests remain, restore original function
                active_tests = [tid for tid, data in self.test_network_calls.items() if data is not None]
                if not active_tests and hasattr(urllib.request, '_original_urlopen'):
                    urllib.request.urlopen = urllib.request._original_urlopen
                    delattr(urllib.request, '_trim_telemetry_patched')
                    delattr(urllib.request, '_original_urlopen')
        except Exception:
            # Silently handle errors - telemetry should not break tests
            pass
