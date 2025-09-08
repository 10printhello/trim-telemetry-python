"""
Trim Telemetry - Rich test telemetry collection package
"""

__version__ = "0.1.0"
__author__ = "Trim Team"

from .django_instrumentation import DjangoInstrumentation
from .pytest_instrumentation import PytestInstrumentation
from .unittest_instrumentation import UnittestInstrumentation

__all__ = [
    "DjangoInstrumentation",
    "PytestInstrumentation",
    "UnittestInstrumentation",
]
