from datetime import timedelta
import voluptuous as vol
import logging

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_API_TOKEN, CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from ohdear import OhDear, NotFoundException, UnauthorizedException

import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_SITE_ID, DEFAULT_SCAN_INTERVAL

_LOGGER: logging.Logger = logging.getLogger(__package__)

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SITE_ID): cv.positive_int,
        vol.Required(CONF_API_TOKEN): cv.string,
    }
)

DESCRIPTION_PLACEHOLDERS = {"api_tokens_url": "https://ohdear.app/user/api-tokens"}


class OhDearConfigFlow(ConfigFlow, domain=DOMAIN):
    """The configuration flow for an Oh Dear system."""

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Ask the user for an API token, site id, and a name for the system."""
        errors = {}
        if user_input:
            try:
                site = await self.hass.async_add_executor_job(
                    lambda: get_site(
                        api_token=user_input[CONF_API_TOKEN],
                        site_id=user_input[CONF_SITE_ID],
                    )
                )
                if site:
                    # Make sure we're not configuring the same device
                    await self.async_set_unique_id(f"ohdear_{user_input[CONF_SITE_ID]}")
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=f'Oh Dear ({site["label"]})',
                        data=user_input,
                    )
            except UnauthorizedException:
                errors[CONF_API_TOKEN] = "invalid_api_token"
            except NotFoundException:
                errors[CONF_SITE_ID] = "invalid_site_id"
            else:
                errors[CONF_API_TOKEN] = "server_error"

        return self.async_show_form(
            step_id="user",
            description_placeholders=DESCRIPTION_PLACEHOLDERS,
            data_schema=CONFIG_SCHEMA,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return OhDearOptionsFlowHandler(config_entry)


class OhDearOptionsFlowHandler(OptionsFlow):
    """Config flow options handler for Oh Dear."""

    def __init__(self, config_entry: ConfigEntry):
        """Initialize options flow."""
        self.config_entry = config_entry
        # Cast from MappingProxy to dict to allow update.
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            self.options.update(user_input)
            coordinator = self.hass.data[DOMAIN][self.config_entry.entry_id]

            update_interval = timedelta(
                minutes=self.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            )

            _LOGGER.debug("Updating coordinator, update_interval: %s", update_interval)

            coordinator.update_interval = update_interval

            return self.async_create_entry(title="", data=self.options)

        options_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=self.config_entry.options.get(
                        CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=1)),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
        )


def get_site(api_token: str, site_id: int):
    return OhDear(api_token=api_token).sites.show(site_id)
