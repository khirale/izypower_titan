from __future__ import annotations

import logging
from typing import Any
from datetime import timedelta
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady


from .const import (
    DOMAIN,
    PLATFORMS,
    DEFAULT_SCAN_INTERVAL,
)
from .coordinator import IzypowerTitanCoordinator

_LOGGER = logging.getLogger(__name__)



# ---------------------------------------------------------
# SETUP
# ---------------------------------------------------------
async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    try:
        coordinator = IzypowerTitanCoordinator(hass, entry)
        await coordinator.async_config_entry_first_refresh()

        hass.data[DOMAIN][entry.entry_id] = coordinator
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        entry.async_on_unload(entry.add_update_listener(async_update_listener))


        _LOGGER.info("Izypower Titan setup complete for host: %s", entry.data.get("host"))
        return True

    except Exception as err:
        _LOGGER.exception("Unexpected error occurred while setting config entry.")
        if entry.entry_id in hass.data.get(DOMAIN, {}):
            del hass.data[DOMAIN][entry.entry_id]
        raise ConfigEntryNotReady from err


# ---------------------------------------------------------
# UNLOAD / UPDATE
# ---------------------------------------------------------
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if DOMAIN not in hass.data or entry.entry_id not in hass.data[DOMAIN]:
        return True

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()

    return unload_ok


async def async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    coordinator: IzypowerTitanCoordinator = hass.data[DOMAIN][entry.entry_id]
    new_interval = entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)
    coordinator.update_interval = timedelta(seconds=new_interval)

    _LOGGER.info(
        "Izypower Titan options updated — scan_interval=%ss, charge=%sW, discharge=%sW",
        new_interval,
        entry.options.get("max_charge_power", DEFAULT_MAX_CHARGE_POWER),
        entry.options.get("max_discharge_power", DEFAULT_MAX_DISCHARGE_POWER),
    )
