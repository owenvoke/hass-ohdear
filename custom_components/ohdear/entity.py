from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.helpers.device_registry import DeviceEntryType
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import OhDearUpdateCoordinator, _LOGGER, DOMAIN


class OhDearSensorEntity(CoordinatorEntity[OhDearUpdateCoordinator], SensorEntity):
    """Representation of an Oh Dear sensor."""

    entity_description: SensorEntityDescription

    def __init__(self, coordinator: OhDearUpdateCoordinator, description: SensorEntityDescription):
        """Initialize the sensor and set the update coordinator."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_name = f"{self.coordinator.data['label']} {self.entity_description.name}"
        self._attr_unique_id = f"{self.coordinator.data['id']}_{description.key}"

    @property
    def native_value(self) -> str:
        for check in self.coordinator.data['checks']:
            if check['type'] == self.entity_description.key and check['enabled']:
                return check['latest_run_result']

        return STATE_UNAVAILABLE

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            name=self.coordinator.data['label'],
            entry_type=DeviceEntryType.SERVICE,
            identifiers={(DOMAIN, f'{self.coordinator.data["id"]}')},
            manufacturer='Oh Dear',
            configuration_url=f'https://ohdear.app/sites/{self.coordinator.data["id"]}/active-checks'
        )
