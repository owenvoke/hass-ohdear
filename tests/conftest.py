"""Fixtures for Oh Dear tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest

USER = {"id": 42, "name": "Owen", "email": "owen@example.com", "teams": []}


def make_site(site_id: int, label: str) -> dict:
    return {
        "id": site_id,
        "label": label,
        "checks": [
            {
                "id": site_id * 10 + 1,
                "type": "uptime",
                "label": "Uptime",
                "enabled": True,
                "latest_run_ended_at": "2026-10-16 10:00:00",
                "latest_run_result": "succeeded",
                "summary": "Up",
            },
            {
                "id": site_id * 10 + 2,
                "type": "performance",
                "label": "Performance",
                "enabled": False,
                "latest_run_ended_at": None,
                "latest_run_result": "pending",
                "summary": "",
            },
        ],
    }


SITES = {1: make_site(1, "Alpha"), 2: make_site(2, "Beta"), 3: make_site(3, "Gamma")}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Enable custom integrations in every test."""


@pytest.fixture
def mock_ohdear() -> Generator[MagicMock]:
    """Patch the Oh Dear client everywhere it is constructed."""
    client = MagicMock()
    client.me.return_value = USER
    client.sites.all.return_value = {"data": [SITES[1], SITES[2]]}
    client.sites.show.side_effect = lambda site_id: SITES[site_id]

    with (
        patch("custom_components.ohdear.config_flow.OhDear", return_value=client),
        patch("custom_components.ohdear.coordinator.OhDear", return_value=client),
    ):
        yield client
