from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from custom_components.ohdear import OhDearUpdateCoordinator, _LOGGER


class OhDearSensorEntity(CoordinatorEntity[OhDearUpdateCoordinator], SensorEntity):
    """Representation of an Oh Dear sensor."""

    entity_description: SensorEntityDescription

    def __init__(self, coordinator: OhDearUpdateCoordinator, description: SensorEntityDescription):
        """Initialize the sensor and set the update coordinator."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{self.coordinator.data['id']}_{description.key}"

    @property
    def native_value(self) -> str:
        for check in self.coordinator.data.get('checks'):
            if check.get('type') == self.entity_description.key:
                if check.get('enabled'):
                    return check.get('latest_run_result')
                else:
                    return STATE_UNAVAILABLE
        _LOGGER.warning(f'Unable to find Check entry for {self.entity_description.key} in API response')
