import logging
from datetime import timedelta

import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
import ohdear as ohdear_sdk

_LOGGER = logging.getLogger(__name__)


class OhDearUpdateCoordinator(DataUpdateCoordinator[ohdear_sdk.Site]):
    """Coordinates updates between all Oh Dear sensors defined."""

    def __init__(self, hass: HomeAssistant, name: str, api_token: str, site_id: int) -> None:
        self._ohdear: ohdear_sdk.OhDear = ohdear_sdk.OhDear(api_token=api_token)
        self._site_id: int = site_id

        """Initialize the UpdateCoordinator for Oh Dear sensors."""
        super().__init__(
            hass,
            _LOGGER,
            name=name,
            update_interval=timedelta(minutes=5),
        )

    async def _async_update_data(self) -> ohdear_sdk.Site:
        async with async_timeout.timeout(5):
            return await self.hass.async_add_executor_job(
                lambda: self._ohdear.sites.show(self._site_id)
            )
