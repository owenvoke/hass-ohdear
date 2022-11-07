import logging
from datetime import timedelta

import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from ohdear import Site, OhDear

_LOGGER = logging.getLogger(__name__)


class OhDearUpdateCoordinator(DataUpdateCoordinator[Site]):
    """Coordinates updates between all Oh Dear sensors defined."""

    def __init__(self, hass: HomeAssistant, name: str, api_token: str, site_id: int,
                 update_interval: timedelta) -> None:
        self._ohdear = OhDear(api_token=api_token)
        self._site_id = site_id

        """Initialize the UpdateCoordinator for Oh Dear sensors."""
        super().__init__(
            hass,
            _LOGGER,
            name=name,
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> Site:
        async with async_timeout.timeout(5):
            return await self.hass.async_add_executor_job(
                lambda: self._ohdear.sites.show(self._site_id)
            )
