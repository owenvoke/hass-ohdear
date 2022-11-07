import logging
from datetime import timedelta

from homeassistant.components.sensor import SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import OhDearUpdateCoordinator
from .entity import OhDearSensorEntity

DOMAIN = 'ohdear'

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

ICON = 'mdi:list-status'

SCAN_INTERVAL = timedelta(minutes=5)

SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key="uptime",
        name="Uptime",
    ),
    SensorEntityDescription(
        key="performance",
        name="Performance",
    ),
    SensorEntityDescription(
        key="broken_links",
        name="Broken Links",
    ),
    SensorEntityDescription(
        key="mixed_content",
        name="Mixed Content",
    ),
    SensorEntityDescription(
        key="certificate_health",
        name="Certificate Health",
    ),
    SensorEntityDescription(
        key="certificate_transparency",
        name="Certificate Transparency",
    ),
    SensorEntityDescription(
        key="dns",
        name="DNS",
    ),
    SensorEntityDescription(
        key="application_health",
        name="Application Health",
    ),
    SensorEntityDescription(
        key="domain",
        name="Domain",
    ),
    SensorEntityDescription(
        key="cron",
        name="Scheduled Tasks",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up all sensors for this entry."""
    coordinator: OhDearUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        OhDearSensorEntity(coordinator, description) for description in SENSORS
    )
