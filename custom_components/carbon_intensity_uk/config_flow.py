"""Adds config flow for Carbon Intensity."""

import asyncio
import logging

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

_LOGGER = logging.getLogger(__name__)

from carbonintensity.client import (
    CarbonIntensityApiError,
    Client as CarbonIntentisityApi,
    InvalidPostcodeError,
)

from custom_components.carbon_intensity_uk.const import (  # pylint: disable=unused-import
    CONF_POSTCODE,
    DOMAIN,
    PLATFORMS,
)


class CarbonIntensityFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Carbon Intensity UK."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize."""
        self._errors = {}

    async def async_step_user(
        self, user_input=None  # pylint: disable=bad-continuation
    ):
        """Handle a flow initialized by the user."""
        self._errors = {}

        if user_input is not None:
            client = CarbonIntentisityApi(user_input[CONF_POSTCODE])
            error = await self._async_validate_postcode(client)
            if error is None:
                _LOGGER.debug("Input is valid")
                # Store the normalized outward code, not the raw input.
                return self.async_create_entry(
                    title=client.postcode, data={CONF_POSTCODE: client.postcode}
                )
            _LOGGER.debug("Input not valid: %s", error)
            self._errors["base"] = error

            return await self._show_config_form(user_input)

        return await self._show_config_form(user_input)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return CarbonIntensityOptionsFlowHandler(config_entry)

    async def _show_config_form(self, user_input):  # pylint: disable=unused-argument
        """Show the configuration form to edit location data."""
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_POSTCODE): str,
                }
            ),
            errors=self._errors,
        )

    async def _async_validate_postcode(self, client):
        """Return an error key if the postcode cannot be used, else None."""
        try:
            await client.async_get_data()
            return None
        except InvalidPostcodeError as exception:
            _LOGGER.debug(exception)
            return "invalid_postcode"
        except (aiohttp.ClientError, asyncio.TimeoutError) as exception:
            _LOGGER.debug(exception)
            return "cannot_connect"
        except CarbonIntensityApiError as exception:
            _LOGGER.debug(exception)
            return "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected error validating postcode")
            return "unknown"


class CarbonIntensityOptionsFlowHandler(config_entries.OptionsFlow):
    """Carbon Intensity UK config flow options handler."""

    def __init__(self, config_entry):
        """Initialize HACS options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)

    async def async_step_init(self, user_input=None):  # pylint: disable=unused-argument
        """Manage the options."""
        return await self.async_step_user()

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if user_input is not None:
            self.options.update(user_input)
            return await self._update_options()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(x, default=self.options.get(x, True)): bool
                    for x in sorted(PLATFORMS)
                }
            ),
        )

    async def _update_options(self):
        """Update config entry options."""
        return self.async_create_entry(
            title=self.config_entry.data.get(CONF_POSTCODE), data=self.options
        )
