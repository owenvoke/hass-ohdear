from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_API_TOKEN, CONF_SCAN_INTERVAL
from homeassistant.data_entry_flow import FlowResult
from ohdear import OhDear, NotFoundException, UnauthorizedException

import homeassistant.helpers.config_validation as cv

from .const import DOMAIN, CONF_SITE_ID, DEFAULT_SCAN_INTERVAL

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SITE_ID): cv.positive_int,
        vol.Required(CONF_API_TOKEN): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): vol.All(
            vol.Coerce(int), vol.Range(min=1)
        ),
    }
)


class OhDearConfigFlow(ConfigFlow, domain=DOMAIN):
    """The configuration flow for an Oh Dear system."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
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
            step_id="user", data_schema=CONFIG_SCHEMA, errors=errors
        )


def get_site(api_token: str, site_id: int):
    return OhDear(api_token=api_token).sites.show(site_id)
