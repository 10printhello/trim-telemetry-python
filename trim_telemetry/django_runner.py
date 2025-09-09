"""
Minimal Django test runner for debugging
"""

import json
from django.test.runner import DiscoverRunner


class TrimTelemetryRunner(DiscoverRunner):
    """Minimal test runner - does nothing but inherit from Django's runner."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print(f"DEBUG: TrimTelemetryRunner initialized with args: {args}, kwargs: {kwargs}", flush=True)

    def run_suite(self, suite, **kwargs):
        """Run test suite - just use standard Django behavior."""
        print(f"DEBUG: Running suite with {suite.countTestCases()} tests", flush=True)
        return super().run_suite(suite, **kwargs)

    def run_tests(self, test_labels=None, **kwargs):
        """Run tests - just use standard Django behavior."""
        print(f"DEBUG: run_tests called with test_labels: {test_labels}, kwargs: {kwargs}", flush=True)
        return super().run_tests(test_labels, **kwargs)