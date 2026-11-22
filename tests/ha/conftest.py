"""Fixtures for Home Assistant tests (need pytest-homeassistant-custom-component)."""

import pytest

pytest.importorskip("pytest_homeassistant_custom_component")


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load custom_components/ from the repo root."""
    yield
