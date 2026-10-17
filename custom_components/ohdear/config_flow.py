"""Config flow for the Oh Dear integration."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import requests
import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigEntryState,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryData,
    ConfigSubentryFlow,
    OptionsFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_API_TOKEN, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from ohdear import OhDear, OhDearException, UnauthorizedException, UserInfo

from .const import (
    CONF_SITE_ID,
    CONF_SITES,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    SUBENTRY_TYPE_SITE,
)
from .coordinator import OhDearConfigEntry

_LOGGER = logging.getLogger(__name__)

API_TOKEN_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_TOKEN): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
    }
)

OPTIONS_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): NumberSelector(
            NumberSelectorConfig(
                min=1,
                max=1440,
                step=1,
                mode=NumberSelectorMode.BOX,
                unit_of_measurement="min",
            )
        ),
    }
)

DESCRIPTION_PLACEHOLDERS = {"api_tokens_url": "https://ohdear.app/user/api-tokens"}


async def _async_get_user(
    hass: HomeAssistant, api_token: str, errors: dict[str, str]
) -> UserInfo | None:
    """Validate an API token, returning its user or recording an error."""
    try:
        return await hass.async_add_executor_job(OhDear(api_token=api_token).me)
    except UnauthorizedException:
        errors["base"] = "invalid_auth"
    except OhDearException, requests.RequestException:
        errors["base"] = "cannot_connect"
    except Exception:
        _LOGGER.exception("Unexpected error validating the Oh Dear API token")
        errors["base"] = "unknown"
    return None


def _site_options(sites: dict[str, str]) -> list[SelectOptionDict]:
    return [
        SelectOptionDict(value=site_id, label=label)
        for site_id, label in sorted(sites.items(), key=lambda s: s[1].casefold())
    ]


def _fetch_site_labels(client: OhDear) -> dict[str, str]:
    """Return the account's sites as {site id: label}."""
    return {str(site["id"]): site["label"] for site in client.sites.all()["data"]}


class OhDearConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for an Oh Dear account."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialise the flow."""
        self._api_token: str | None = None
        self._title: str | None = None
        self._sites: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for an API token."""
        errors: dict[str, str] = {}
        if user_input is not None:
            api_token = user_input[CONF_API_TOKEN]
            if user := await _async_get_user(self.hass, api_token, errors):
                await self.async_set_unique_id(str(user["id"]))
                self._abort_if_unique_id_configured()

                self._api_token = api_token
                self._title = f"Oh Dear ({user['email']})"
                return await self.async_step_sites()

        return self.async_show_form(
            step_id="user",
            data_schema=API_TOKEN_SCHEMA,
            description_placeholders=DESCRIPTION_PLACEHOLDERS,
            errors=errors,
        )

    async def async_step_sites(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose which sites to monitor."""
        assert self._api_token is not None
        assert self._title is not None

        if user_input is not None:
            subentries = [
                ConfigSubentryData(
                    data={CONF_SITE_ID: int(site_id)},
                    subentry_type=SUBENTRY_TYPE_SITE,
                    title=self._sites[site_id],
                    unique_id=site_id,
                )
                for site_id in user_input.get(CONF_SITES, [])
            ]
            return self.async_create_entry(
                title=self._title,
                data={CONF_API_TOKEN: self._api_token},
                subentries=subentries,
            )

        try:
            self._sites = await self.hass.async_add_executor_job(
                _fetch_site_labels, OhDear(api_token=self._api_token)
            )
        except OhDearException, requests.RequestException:
            return self.async_abort(reason="cannot_connect")

        return self.async_show_form(
            step_id="sites",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_SITES, default=[]): SelectSelector(
                        SelectSelectorConfig(
                            options=_site_options(self._sites),
                            multiple=True,
                            mode=SelectSelectorMode.LIST,
                        )
                    ),
                }
            ),
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle a rejected API token."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a new API token for the same account."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()

        if user_input is not None:
            api_token = user_input[CONF_API_TOKEN]
            if user := await _async_get_user(self.hass, api_token, errors):
                await self.async_set_unique_id(str(user["id"]))
                if entry.unique_id is not None:
                    self._abort_if_unique_id_mismatch(reason="wrong_account")

                updates = {
                    "data_updates": {CONF_API_TOKEN: api_token},
                    "unique_id": str(user["id"]),
                }
                # A loaded entry is reloaded by its update listener; one that
                # failed setup has no listener, so it needs an explicit reload.
                if entry.update_listeners:
                    return self.async_update_and_abort(entry, **updates)
                return self.async_update_reload_and_abort(entry, **updates)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=API_TOKEN_SCHEMA,
            description_placeholders=DESCRIPTION_PLACEHOLDERS,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return OhDearOptionsFlow()

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return the subentry types this integration supports."""
        return {SUBENTRY_TYPE_SITE: SiteSubentryFlow}


class OhDearOptionsFlow(OptionsFlow):
    """Options for an Oh Dear account."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                OPTIONS_SCHEMA, self.config_entry.options
            ),
        )


class SiteSubentryFlow(ConfigSubentryFlow):
    """Add an Oh Dear site to an account."""

    def __init__(self) -> None:
        """Initialise the flow."""
        self._sites: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Choose a site that isn't monitored yet."""
        entry: OhDearConfigEntry = self._get_entry()
        if entry.state is not ConfigEntryState.LOADED:
            return self.async_abort(reason="entry_not_loaded")

        if user_input is not None:
            site_id = user_input[CONF_SITE_ID]
            return self.async_create_entry(
                title=self._sites[site_id],
                data={CONF_SITE_ID: int(site_id)},
                unique_id=site_id,
            )

        try:
            sites = await self.hass.async_add_executor_job(
                _fetch_site_labels, entry.runtime_data.client
            )
        except OhDearException, requests.RequestException:
            return self.async_abort(reason="cannot_connect")

        configured = {
            subentry.unique_id
            for subentry in entry.subentries.values()
            if subentry.subentry_type == SUBENTRY_TYPE_SITE
        }
        self._sites = {
            site_id: label
            for site_id, label in sites.items()
            if site_id not in configured
        }
        if not self._sites:
            return self.async_abort(reason="no_sites")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SITE_ID): SelectSelector(
                        SelectSelectorConfig(
                            options=_site_options(self._sites),
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )
