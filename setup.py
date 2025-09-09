"""
Setup script for trim-telemetry package
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="trim-telemetry",
    version="0.1.0",
    author="Trim Team",
    author_email="team@trim.dev",
    description="Rich test telemetry collection package for Trim",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/10printhello/trim",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Testing",
        "Topic :: Software Development :: Quality Assurance",
    ],
    python_requires=">=3.8",
    install_requires=[
        "django>=3.2",
        "pytest>=6.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "black",
            "flake8",
            "mypy",
        ],
    },
    entry_points={
        "console_scripts": [
            # Test runners
            "trim-django=trim_telemetry.django_runner:TrimTelemetryRunner",
            "trim-pytest=trim_telemetry.pytest_runner:main",
            "trim-unittest=trim_telemetry.unittest_runner:main",
        ],
    },
)
