"""Pytest configuration — Ch.22 testing pyramid markers."""

from __future__ import annotations

import pytest


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line("markers", "unit: Unit-level tests (Ch.22)")
    config.addinivalue_line("markers", "integration: Integration tests (Ch.22)")
    config.addinivalue_line("markers", "e2e: End-to-end scenarios (Ch.22)")
    config.addinivalue_line("markers", "performance: Performance tests (Ch.22)")
    config.addinivalue_line("markers", "security: Security tests (Ch.22)")
    config.addinivalue_line("markers", "ai: AI validation tests (Ch.22)")
    config.addinivalue_line("markers", "regression: Regression tests (Ch.22)")
