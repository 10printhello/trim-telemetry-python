"""
Django-specific telemetry collection
"""

import urllib.request
from django.db import connection, reset_queries
from django.conf import settings
from .base_telemetry import BaseTelemetryCollector


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

            # Enable query logging in settings (Django best practice)
            if not getattr(settings, "DEBUG", False):
                settings.DEBUG = True
        except Exception:
            # Silently handle errors - telemetry should not break tests
            pass

    def start_test(self, test, test_id: str = None):
        """Start tracking a Django test with database and network monitoring."""
        super().start_test(test, test_id)

        if test_id is None:
            test_id = str(test)

        # Reset queries before each test (Django best practice)
        reset_queries()

        # Store initial query count for this test
        self.test_queries[test_id] = len(connection.queries)

        # Start network call monitoring for this test
        self.start_network_monitoring(test_id)

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

        except Exception:
            # If there's any error collecting database telemetry, return zeros
            return self._get_empty_database_telemetry()

    def start_network_monitoring(self, test_id: str):
        """Start monitoring network calls for a Django test."""
        try:
            # Store original urllib methods and initialize call tracking
            self.test_network_calls[test_id] = {
                "calls": [],
                "original_urlopen": urllib.request.urlopen,
                "original_request": getattr(urllib.request, "Request", None),
            }

            # Create a simple tracked version that just logs URLs
            def tracked_urlopen(*args, **kwargs):
                # Only track if this is called during our test's execution
                if test_id not in self.test_network_calls:
                    # Fall back to original if test is no longer active
                    return self.test_network_calls.get(test_id, {}).get(
                        "original_urlopen", urllib.request.urlopen
                    )(*args, **kwargs)

                # Just capture the URL - no timing, no blocking
                url = args[0] if args else kwargs.get("url", "unknown")
                url_str = str(url)

                # Make the actual call using the original function (no timing)
                result = self.test_network_calls[test_id]["original_urlopen"](
                    *args, **kwargs
                )

                # Log the call (just URL, no duration or status)
                self.test_network_calls[test_id]["calls"].append(
                    {
                        "url": url_str,
                    }
                )

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
                # Restore original urllib methods
                network_data = self.test_network_calls[test_id]
                if "original_urlopen" in network_data:
                    urllib.request.urlopen = network_data["original_urlopen"]

                # Clean up
                del self.test_network_calls[test_id]
        except Exception:
            # Silently handle errors - telemetry should not break tests
            pass
