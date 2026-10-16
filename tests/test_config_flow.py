"""Tests for the Oh Dear config, subentry and options flows."""

from __future__ import annotations

from unittest.mock import MagicMock

from homeassistant import config_entries
from homeassistant.const import CONF_API_TOKEN, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from ohdear import UnauthorizedException
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ohdear.const import CONF_SITE_ID, DOMAIN


async def test_user_flow_creates_entry_with_sites(
    hass: HomeAssistant, mock_ohdear: MagicMock
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_TOKEN: "token"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "sites"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"sites": ["2"]}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Oh Dear (owen@example.com)"
    assert result["data"] == {CONF_API_TOKEN: "token"}

    entry = result["result"]
    assert entry.unique_id == "42"
    assert [(s.title, dict(s.data)) for s in entry.subentries.values()] == [
        ("Beta", {CONF_SITE_ID: 2})
    ]
    await hass.async_block_till_done()
    assert hass.states.get("sensor.beta_uptime").state == "succeeded"


async def test_user_flow_invalid_token(
    hass: HomeAssistant, mock_ohdear: MagicMock
) -> None:
    mock_ohdear.me.side_effect = UnauthorizedException("nope")
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_TOKEN: "bad"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}


async def test_user_flow_network_error(
    hass: HomeAssistant, mock_ohdear: MagicMock
) -> None:
    import requests

    mock_ohdear.me.side_effect = requests.ConnectionError()
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_TOKEN: "token"}
    )
    assert result["errors"] == {"base": "cannot_connect"}


async def test_add_site_subentry(hass: HomeAssistant, mock_ohdear: MagicMock) -> None:
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

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, "site"), context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    # Alpha is already configured, so only Beta is offered.
    options = result["data_schema"].schema[CONF_SITE_ID].config["options"]
    assert [o["value"] for o in options] == ["2"]

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"], {CONF_SITE_ID: "2"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()

    assert hass.states.get("sensor.alpha_uptime") is not None
    assert hass.states.get("sensor.beta_uptime").state == "succeeded"


async def test_options_flow(hass: HomeAssistant, mock_ohdear: MagicMock) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, version=2, unique_id="42", data={CONF_API_TOKEN: "token"}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_SCAN_INTERVAL: 10}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert entry.options == {CONF_SCAN_INTERVAL: 10}
    assert entry.runtime_data.update_interval.total_seconds() == 600


async def test_reauth(hass: HomeAssistant, mock_ohdear: MagicMock) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, version=2, unique_id="42", data={CONF_API_TOKEN: "old"}
    )
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_TOKEN: "new"}
    )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_API_TOKEN] == "new"


async def test_reauth_wrong_account(
    hass: HomeAssistant, mock_ohdear: MagicMock
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, version=2, unique_id="7", data={CONF_API_TOKEN: "old"}
    )
    entry.add_to_hass(hass)
    result = await entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_TOKEN: "new"}
    )
    assert result["reason"] == "wrong_account"
