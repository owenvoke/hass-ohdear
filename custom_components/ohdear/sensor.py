"""Sensors for Oh Dear checks."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import CONF_SITE_ID, SUBENTRY_TYPE_SITE
from .coordinator import OhDearConfigEntry
from .entity import OhDearSensorEntity

PARALLEL_UPDATES = 0

SENSORS: tuple[SensorEntityDescription, ...] = tuple(
    SensorEntityDescription(key=key, translation_key=key)
    for key in (
        "uptime",
        "performance",
        "broken_links",
        "mixed_content",
        "certificate_health",
        "certificate_transparency",
        "dns",
        "application_health",
        "domain",
        "cron",
    )
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: OhDearConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up a sensor for each check of each configured site."""
    coordinator = entry.runtime_data

    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type != SUBENTRY_TYPE_SITE:
            continue

        site_id: int = subentry.data[CONF_SITE_ID]
        site = coordinator.data.get(site_id)
        check_types = {check["type"] for check in site["checks"]} if site else set()

        async_add_entities(
            (
                OhDearSensorEntity(coordinator, description, site_id, subentry.title)
                for description in SENSORS
                if description.key in check_types
            ),
            config_subentry_id=subentry_id,
        )
