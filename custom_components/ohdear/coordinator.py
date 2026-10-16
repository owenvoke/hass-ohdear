"""Data update coordinator for Oh Dear."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import timedelta
from typing import Any

import requests
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_API_TOKEN, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from ohdear import (
    NotFoundException,
    OhDear,
    OhDearException,
    Site,
    UnauthorizedException,
)

from .const import CONF_SITE_ID, DEFAULT_SCAN_INTERVAL, DOMAIN, SUBENTRY_TYPE_SITE

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = 30

type OhDearConfigEntry = ConfigEntry[OhDearUpdateCoordinator]


class OhDearUpdateCoordinator(DataUpdateCoordinator[dict[int, Site]]):
    """Fetch every site configured as a subentry of one Oh Dear account."""

    config_entry: OhDearConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: OhDearConfigEntry) -> None:
        """Initialise the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=DOMAIN,
            update_interval=timedelta(
                minutes=int(
                    config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                )
            ),
        )
        self.client = OhDear(api_token=config_entry.data[CONF_API_TOKEN])

    async def _async_setup(self) -> None:
        """Set the account's unique ID on entries migrated from version 1."""
        if self.config_entry.unique_id is not None:
            return

        user = await self._async_call(self.client.me)
        unique_id = str(user["id"])

        # Two migrated tokens can belong to the same account; leave the second
        # without a unique ID rather than clash with the first.
        if self.hass.config_entries.async_entry_for_domain_unique_id(DOMAIN, unique_id):
            _LOGGER.warning(
                "Another Oh Dear entry already uses the account %s; consider "
                "moving the sites from %s onto it",
                user["email"],
                self.config_entry.title,
            )
            return

        self.hass.config_entries.async_update_entry(
            self.config_entry, unique_id=unique_id
        )

    async def _async_update_data(self) -> dict[int, Site]:
        """Fetch the latest check results for every configured site."""
        site_ids = [
            subentry.data[CONF_SITE_ID]
            for subentry in self.config_entry.subentries.values()
            if subentry.subentry_type == SUBENTRY_TYPE_SITE
        ]
        return await self._async_call(self._fetch_sites, site_ids)

    def _fetch_sites(self, site_ids: list[int]) -> dict[int, Site]:
        sites: dict[int, Site] = {}
        for site_id in site_ids:
            try:
                sites[site_id] = self.client.sites.show(site_id)
            except NotFoundException:
                _LOGGER.warning("Site %s no longer exists in Oh Dear", site_id)
        return sites

    async def _async_call(self, func: Callable[..., Any], *args: Any) -> Any:
        """Run a blocking SDK call and map its errors to Home Assistant ones."""
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                return await self.hass.async_add_executor_job(func, *args)
        except UnauthorizedException as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN, translation_key="invalid_auth"
            ) from err
        except (OhDearException, requests.RequestException, TimeoutError) as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="update_failed",
                translation_placeholders={"error": str(err)},
            ) from err
