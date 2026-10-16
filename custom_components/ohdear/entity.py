"""Base entity for Oh Dear."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from ohdear import Check

from .const import DOMAIN
from .coordinator import OhDearUpdateCoordinator


class OhDearSensorEntity(CoordinatorEntity[OhDearUpdateCoordinator], SensorEntity):
    """The latest result of one Oh Dear check on a site."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: OhDearUpdateCoordinator,
        description: SensorEntityDescription,
        site_id: int,
        site_label: str,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._site_id = site_id
        self._attr_unique_id = f"{site_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, str(site_id))},
            name=site_label,
            entry_type=DeviceEntryType.SERVICE,
            manufacturer="Oh Dear",
            configuration_url=f"https://ohdear.app/sites/{site_id}/active-checks",
        )

    @property
    def _check(self) -> Check | None:
        if (site := self.coordinator.data.get(self._site_id)) is None:
            return None
        return next(
            (
                check
                for check in site["checks"]
                if check["type"] == self.entity_description.key and check["enabled"]
            ),
            None,
        )

    @property
    def available(self) -> bool:
        """Return whether the check exists and is enabled."""
        return super().available and self._check is not None

    @property
    def native_value(self) -> str | None:
        """Return the result of the check's latest run."""
        if (check := self._check) is None:
            return None
        return check["latest_run_result"]

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the check's summary and when it last ran."""
        if (check := self._check) is None:
            return None
        return {
            "summary": check.get("summary"),
            "latest_run_ended_at": check.get("latest_run_ended_at"),
        }
