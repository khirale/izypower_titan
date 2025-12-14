import logging
from typing import Any
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
)
from .izypower_api import IzypowerAPI

_LOGGER = logging.getLogger(__name__)


class IzypowerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input.get(CONF_PORT, DEFAULT_PORT)
            scan_interval = user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

            api = IzypowerAPI(host, port, async_get_clientsession(self.hass))
            try:
                await api.fetch_data(["1664"])
            except Exception as e:
                _LOGGER.error(
                    "Erreur de connexion à Izypower Titan (%s): %s",
                    host,
                    e
                )
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"Izypower Titan ({host})",
                    data={
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_SCAN_INTERVAL: scan_interval,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
            }),
            errors=errors,
        )