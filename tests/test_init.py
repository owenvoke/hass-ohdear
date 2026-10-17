"""Tests for Oh Dear setup and migration."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_API_TOKEN, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from ohdear import UnauthorizedException
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ohdear.const import CONF_SITE_ID, DOMAIN


def _site_entry(site_id: int, label: str, token: str = "token") -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        version=1,
        title=f"Oh Dear ({label})",
        unique_id=f"ohdear_{site_id}",
        data={CONF_API_TOKEN: token, CONF_SITE_ID: site_id},
    )


async def test_sensors(hass: HomeAssistant, mock_ohdear: MagicMock) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id="42",
        data={CONF_API_TOKEN: "token"},
        subentries_data=[
            {
                "data": {CONF_SITE_ID: 1},
                "subentry_type": "site",
                "title": "Alpha",
                "unique_id": "1",
            }
        ],
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    uptime = hass.states.get("sensor.alpha_uptime")
    assert uptime.state == "succeeded"
    assert uptime.attributes["summary"] == "Up"
    # Disabled check: entity exists but is unavailable.
    assert hass.states.get("sensor.alpha_performance").state == STATE_UNAVAILABLE
    # Checks the site doesn't have aren't created.
    assert hass.states.get("sensor.alpha_dns") is None


async def test_auth_failure_starts_reauth(
    hass: HomeAssistant, mock_ohdear: MagicMock
) -> None:
    mock_ohdear.sites.show.side_effect = UnauthorizedException("nope")
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=2,
        unique_id="42",
        data={CONF_API_TOKEN: "token"},
        subentries_data=[
            {
                "data": {CONF_SITE_ID: 1},
                "subentry_type": "site",
                "title": "Alpha",
                "unique_id": "1",
            }
        ],
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress()
    assert [f["context"]["source"] for f in flows] == ["reauth"]


async def test_migrate_v1_entries(hass: HomeAssistant, mock_ohdear: MagicMock) -> None:
    """Two sites sharing a token merge into one entry and keep their entities."""
    alpha = _site_entry(1, "Alpha")
    beta = _site_entry(2, "Beta")
    other = _site_entry(3, "Gamma", token="other")
    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)

    for entry in (alpha, beta, other):
        entry.add_to_hass(hass)
    for entry, site_id in ((alpha, 1), (beta, 2)):
        device_registry.async_get_or_create(
            config_entry_id=entry.entry_id, identifiers={(DOMAIN, str(site_id))}
        )
        entity_registry.async_get_or_create(
            "sensor",
            DOMAIN,
            f"{site_id}_uptime",
            config_entry=entry,
            suggested_object_id=f"site_{site_id}_uptime",
        )

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    entries = hass.config_entries.async_entries(DOMAIN)
    assert len(entries) == 2
    # A different token stays a separate entry.
    other = hass.config_entries.async_get_entry(other.entry_id)
    assert [s.title for s in other.subentries.values()] == ["Gamma"]
    parent = hass.config_entries.async_get_entry(alpha.entry_id)
    assert parent.version == 2
    assert parent.data == {CONF_API_TOKEN: "token"}
    assert parent.unique_id == "42"
    assert parent.state is ConfigEntryState.LOADED
    assert sorted(s.title for s in parent.subentries.values()) == ["Alpha", "Beta"]
    assert hass.config_entries.async_get_entry(beta.entry_id) is None

    subentry_ids = {s.unique_id: s.subentry_id for s in parent.subentries.values()}
    for site_id in (1, 2):
        entity = entity_registry.async_get(f"sensor.site_{site_id}_uptime")
        assert entity.config_entry_id == parent.entry_id
        assert entity.config_subentry_id == subentry_ids[str(site_id)]
        device = device_registry.async_get_device_by_identifier(
            (DOMAIN, str(site_id)), parent.entry_id
        )
        assert device.config_entries == {parent.entry_id}
        assert device.config_entries_subentries == {
            parent.entry_id: {subentry_ids[str(site_id)]}
        }

    # Entity IDs (and history) carry over.
    assert hass.states.get("sensor.site_1_uptime").state == "succeeded"
    assert hass.states.get("sensor.site_2_uptime").state == "succeeded"
