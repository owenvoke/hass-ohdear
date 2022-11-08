"""The Oh Dear integration"""
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform, CONF_API_TOKEN, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_SITE_ID, DEFAULT_SCAN_INTERVAL
from .coordinator import OhDearUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    ohdear_coordinator = OhDearUpdateCoordinator(
        hass=hass,
        name=config_entry.title,
        api_token=config_entry.data[CONF_API_TOKEN],
        site_id=config_entry.data[CONF_SITE_ID],
        update_interval=timedelta(
            minutes=(config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))
        ),
    )

    await ohdear_coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[config_entry.entry_id] = ohdear_coordinator

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data.pop(DOMAIN)

    return unload_ok
