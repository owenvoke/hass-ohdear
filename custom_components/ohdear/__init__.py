"""The Oh Dear integration."""

from __future__ import annotations

from types import MappingProxyType

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import CONF_API_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.typing import ConfigType

from .const import CONF_SITE_ID, DOMAIN, SUBENTRY_TYPE_SITE
from .coordinator import OhDearConfigEntry, OhDearUpdateCoordinator

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Oh Dear integration."""
    await async_migrate_integration(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: OhDearConfigEntry) -> bool:
    """Set up an Oh Dear account from a config entry."""
    coordinator = OhDearUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload when options change or a site is added or removed.
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: OhDearConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_update_listener(hass: HomeAssistant, entry: OhDearConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_integration(hass: HomeAssistant) -> None:
    """Merge version 1 entries (one per site) into one entry per API token.

    Each site becomes a subentry of its account's entry. Entity unique IDs and
    device identifiers are unchanged, so entity IDs and history are kept.
    """
    # Prefer enabled entries as the parent for each token.
    entries = sorted(
        hass.config_entries.async_entries(DOMAIN),
        key=lambda e: e.disabled_by is not None,
    )
    if not any(entry.version == 1 for entry in entries):
        return

    entity_registry = er.async_get(hass)
    device_registry = dr.async_get(hass)
    parents: dict[str, ConfigEntry] = {}

    for entry in entries:
        if entry.version != 1:
            continue

        api_token: str = entry.data[CONF_API_TOKEN]
        site_id: int = entry.data[CONF_SITE_ID]
        parent = parents.setdefault(api_token, entry)

        subentry = ConfigSubentry(
            data=MappingProxyType({CONF_SITE_ID: site_id}),
            subentry_type=SUBENTRY_TYPE_SITE,
            title=_site_title(entry.title),
            unique_id=str(site_id),
        )
        hass.config_entries.async_add_subentry(parent, subentry)

        for entity in er.async_entries_for_config_entry(
            entity_registry, entry.entry_id
        ):
            entity_registry.async_update_entity(
                entity.entity_id,
                config_entry_id=parent.entry_id,
                config_subentry_id=subentry.subentry_id,
            )

        if device := device_registry.async_get_device_by_identifier(
            (DOMAIN, str(site_id)), entry.entry_id
        ):
            device_registry.async_update_device(
                device.id,
                new_config_entry_id=parent.entry_id,
                new_config_subentry_id=subentry.subentry_id,
            )

        if entry is not parent:
            await hass.config_entries.async_remove(entry.entry_id)

    for api_token, parent in parents.items():
        hass.config_entries.async_update_entry(
            parent,
            title="Oh Dear",
            data={CONF_API_TOKEN: api_token},
            # Set from the account on first setup, see the coordinator.
            unique_id=None,
            version=2,
        )


def _site_title(entry_title: str) -> str:
    """Turn a version 1 title of "Oh Dear (<label>)" into "<label>"."""
    if entry_title.startswith("Oh Dear (") and entry_title.endswith(")"):
        return entry_title[len("Oh Dear (") : -1]
    return entry_title
