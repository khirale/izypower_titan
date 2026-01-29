from __future__ import annotations

import logging
from typing import Any
from datetime import timedelta
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
import re


HOST_RE = re.compile(r"izypower_titan_(\d+_\d+_\d+_\d+)")

from .const import (
    DOMAIN,
    PLATFORMS,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_MAX_CHARGE_POWER,
    DEFAULT_MAX_DISCHARGE_POWER,
    CONF_TITAN_COUNT,
    CONF_OVERRIDE_RESPONSIBILITY,
    CHARGE_PER_TITAN,
    DISCHARGE_PER_TITAN,
    CONF_CONNECTION_MODE,
    MODE_CLOUD,
    MAX_ABS_PER_TITAN,
    
)
from .coordinator import IzypowerTitanCoordinator

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------
# DYNAMIC SERVICE SCHEMAS
# ---------------------------------------------------------
def build_charge_schema(max_power: int) -> vol.Schema:
    return vol.Schema({
        vol.Required("power"): vol.All(cv.positive_int, vol.Range(min=0, max=max_power)),
        vol.Optional("soc_limit", default=100): vol.All(cv.positive_int, vol.Range(min=0, max=100)),
        vol.Optional("device_id"): cv.string,
    })


def build_discharge_schema(max_power: int) -> vol.Schema:
    return vol.Schema({
        vol.Required("power"): vol.All(cv.positive_int, vol.Range(min=0, max=max_power)),
        vol.Optional("soc_limit", default=5): vol.All(cv.positive_int, vol.Range(min=0, max=100)),
        vol.Optional("device_id"): cv.string,
    })


SERVICE_DEVICE_SCHEMA = vol.Schema({
    vol.Optional("device_id"): cv.string,
})

SERVICE_CLOUD_CHARGE_SCHEMA = vol.Schema({
    vol.Required("power"): vol.All(cv.positive_int, vol.Range(min=0)),
    vol.Optional("soc_limit", default=100): vol.All(cv.positive_int, vol.Range(min=0, max=100)),
    vol.Optional("device_id"): cv.string,
})

SERVICE_CLOUD_DISCHARGE_SCHEMA = vol.Schema({
    vol.Required("power"): cv.positive_int,
    vol.Optional("device_id"): cv.string,
})


# ---------------------------------------------------------
# SETUP
# ---------------------------------------------------------
async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    try:
        titan_count = entry.data.get(CONF_TITAN_COUNT, 1)
        override = entry.data.get(CONF_OVERRIDE_RESPONSIBILITY, False)

        user_max_c = entry.options.get("max_charge_power")
        user_max_d = entry.options.get("max_discharge_power")

        if override and user_max_c and user_max_d:
            final_max_charge = user_max_c
            final_max_discharge = user_max_d
        else:
            final_max_charge = titan_count * CHARGE_PER_TITAN
            final_max_discharge = titan_count * DISCHARGE_PER_TITAN

        cluster = entry.data.get("cluster", {})
        master = cluster.get("master")
        slaves = cluster.get("slaves", [])

        if not master:
            raise ConfigEntryNotReady(
                "Aucune IP Master définie dans la configuration du cluster"
            )

        hosts = [master] + slaves
        hass.data[DOMAIN][entry.entry_id] = {}

        for host in hosts:
            coordinator = IzypowerTitanCoordinator(
                hass,
                entry,
                host=host,
                max_charge=final_max_charge,
                max_discharge=final_max_discharge,
            )

            await coordinator.async_config_entry_first_refresh()

            hass.data[DOMAIN][entry.entry_id][host] = coordinator

        if entry.data.get(CONF_CONNECTION_MODE) == MODE_CLOUD:
            try:
                master_coordinator = hass.data[DOMAIN][entry.entry_id][master]
                token = await master_coordinator.cloud_api.async_login()
                if token:
                    _LOGGER.info("Initial Cloud login OK during setup")
                else:
                    _LOGGER.warning("Initial Cloud login failed (no token)")
            except Exception as err:
                _LOGGER.warning(
                    "Initial Cloud login error during setup: %s", err
                )

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        entry.async_on_unload(entry.add_update_listener(async_update_listener))

        await async_register_services(hass)

        _LOGGER.info(
            "Izypower Titan setup complete — %s Titans (%s)",
            len(hosts),
            ", ".join(hosts),
        )

        return True

    except Exception as err:
        _LOGGER.exception("Unexpected error occurred while setting config entry.")
        if entry.entry_id in hass.data.get(DOMAIN, {}):
            del hass.data[DOMAIN][entry.entry_id]
        raise ConfigEntryNotReady from err


# ---------------------------------------------------------
# SERVICES
# ---------------------------------------------------------
async def async_register_services(hass: HomeAssistant) -> None:
    async def get_coordinator_from_call(call: ServiceCall,) -> "IzypowerTitanCoordinator":
        hass = call.hass
        domain_data = hass.data[DOMAIN]

        entry_id = call.data.get("entry_id")
        host = call.data.get("host")

        if entry_id and host:
            try:
                return domain_data[entry_id][host]
            except KeyError:
                raise HomeAssistantError(f"Titan introuvable (entry_id={entry_id}, host={host})")

        entity_id = call.data.get("entity_id")
        if entity_id:
            entity_reg = er.async_get(hass)
            entity = entity_reg.async_get(entity_id)

            if not entity or not entity.device_id:
                raise HomeAssistantError("entity_id invalide ou non associé à un device")

            call.data["device_id"] = entity.device_id

        device_id = call.data.get("device_id")
        if device_id:
            device_reg = dr.async_get(hass)
            device = device_reg.async_get(device_id)

            if not device:
                raise HomeAssistantError("device_id invalide")

            device_identifier = None

            for domain, identifier in device.identifiers:
                if domain == DOMAIN:
                    device_identifier = identifier
                    break

            if not device_identifier:
                raise HomeAssistantError("Ce device n’est pas un Titan Izypower")

            for entry_id, coordinators in domain_data.items():
                if device_identifier in coordinators:
                    return coordinators[device_identifier]

            for entry_id, coordinators in domain_data.items():
                for coordinator in coordinators.values():
                    if coordinator.serial_number == device_identifier:
                        return coordinator

            raise HomeAssistantError(
                f"Aucun coordinator trouvé pour Titan {device_identifier}"
            )

        raise HomeAssistantError("Veuillez fournir entry_id+host, entity_id ou device_id")


    async def charge(call: ServiceCall):
        coordinator = await get_coordinator_from_call(call)
        if not coordinator: return
        power = call.data["power"]
        soc_limit = call.data.get("soc_limit", 100)
        max_p = coordinator.max_charge_power
        await coordinator.api.async_charge(power, soc_limit, max_p)
        await coordinator.async_request_refresh()

    async def discharge(call: ServiceCall):
        coordinator = await get_coordinator_from_call(call)
        if not coordinator: return
        power = call.data["power"]
        soc_limit = call.data.get("soc_limit", 5)
        max_p = coordinator.max_discharge_power
        await coordinator.api.async_discharge(power, soc_limit, max_p)
        await coordinator.async_request_refresh()

    async def stop(call: ServiceCall):
        coordinator = await get_coordinator_from_call(call)
        if coordinator:
            await coordinator.api.async_stop()
            await coordinator.async_request_refresh()

    async def set_realtime_mode(call: ServiceCall):
        coordinator = await get_coordinator_from_call(call)
        if coordinator:
            await coordinator.api.async_set_realtime_mode()
            await coordinator.async_request_refresh()

    async def set_intelligent_mode(call: ServiceCall):
        coordinator = await get_coordinator_from_call(call)
        if coordinator:
            await coordinator.api.async_set_working_mode(4) 
            await coordinator.async_request_refresh()

    async def set_selfconsumed_mode(call: ServiceCall):
        coordinator = await get_coordinator_from_call(call)
        if coordinator:
            await coordinator.api.async_set_selfconsumed_mode()
            await coordinator.async_request_refresh()


    async def cloud_charge_manual(call: ServiceCall):
        coordinator = await get_coordinator_from_call(call)
        if not coordinator: return
        sn = coordinator.serial_number
        power = call.data.get("power", 800)
        if sn:
            _LOGGER.info("Appel Charge Cloud pour SN %s à %s W", sn, power)
            await coordinator.cloud_api.async_cloud_manual_charge(sn, power)
            await coordinator.async_request_refresh()

    async def set_cloud_max_charge(call: ServiceCall):
        coordinator = await get_coordinator_from_call(call)
        if not coordinator: return
        sn = coordinator.serial_number
        power = call.data["power"]
        if sn:
            await coordinator.cloud_api.async_set_charge_power(sn, power)
            await coordinator.async_request_refresh()

    async def set_cloud_max_discharge(call: ServiceCall):
        coordinator = await get_coordinator_from_call(call)
        if not coordinator: return
        sn = coordinator.serial_number
        power = call.data["power"]
        if sn:
            await coordinator.cloud_api.async_set_discharge_power(sn, power)
            await coordinator.async_request_refresh()

    async def set_cloud_intelligent_mode(call: ServiceCall):
        coordinator = await get_coordinator_from_call(call)
        if not coordinator: return
        sn = coordinator.serial_number
        if sn:
            await coordinator.cloud_api.async_intelligent_mode(sn)
            await coordinator.async_request_refresh()

    async def set_cloud_standby_mode(call: ServiceCall):
        coordinator = await get_coordinator_from_call(call)
        if not coordinator: return
        sn = coordinator.serial_number
        if sn:
            await coordinator.cloud_api.async_cloud_manual_standby(sn)
            await coordinator.async_request_refresh()

    
    entries = hass.data[DOMAIN].values()
    first_entry = next(iter(entries), None)

    first_coordinator = (
        next(iter(first_entry.values()), None)
        if first_entry
        else None
    )

    charge_limit = getattr(first_coordinator, "max_charge_power", DEFAULT_MAX_CHARGE_POWER) if first_coordinator else DEFAULT_MAX_CHARGE_POWER
    discharge_limit = getattr(first_coordinator, "max_discharge_power", DEFAULT_MAX_DISCHARGE_POWER) if first_coordinator else DEFAULT_MAX_DISCHARGE_POWER

    charge_schema = build_charge_schema(charge_limit)
    discharge_schema = build_discharge_schema(discharge_limit)

    hass.services.async_register(DOMAIN, "charge", charge, schema=charge_schema)
    hass.services.async_register(DOMAIN, "discharge", discharge, schema=discharge_schema)
    hass.services.async_register(DOMAIN, "stop", stop, schema=SERVICE_DEVICE_SCHEMA)
    hass.services.async_register(DOMAIN, "set_realtime_mode", set_realtime_mode, schema=SERVICE_DEVICE_SCHEMA)
    hass.services.async_register(DOMAIN, "set_intelligent_mode", set_intelligent_mode, schema=SERVICE_DEVICE_SCHEMA)
    hass.services.async_register(DOMAIN, "set_selfconsumed_mode", set_selfconsumed_mode, schema=SERVICE_DEVICE_SCHEMA)
    hass.services.async_register(DOMAIN, "cloud_charge_manual", cloud_charge_manual, schema=SERVICE_CLOUD_CHARGE_SCHEMA)
    hass.services.async_register(DOMAIN, "set_cloud_max_charge", set_cloud_max_charge, schema=SERVICE_CLOUD_CHARGE_SCHEMA)
    hass.services.async_register(DOMAIN, "set_cloud_max_discharge", set_cloud_max_discharge, schema=SERVICE_CLOUD_DISCHARGE_SCHEMA)
    hass.services.async_register(DOMAIN, "set_cloud_intelligent_mode", set_cloud_intelligent_mode, schema=SERVICE_DEVICE_SCHEMA)
    hass.services.async_register(DOMAIN, "set_cloud_standby_mode", set_cloud_standby_mode, schema=SERVICE_DEVICE_SCHEMA)

    _LOGGER.info("Izypower Titan services registered successfully.")

# ---------------------------------------------------------
# UNLOAD / UPDATE
# ---------------------------------------------------------
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if DOMAIN not in hass.data or entry.entry_id not in hass.data[DOMAIN]:
        return True

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinators = hass.data[DOMAIN].pop(entry.entry_id)

        for coordinator in coordinators.values():
            await coordinator.async_shutdown()

    return unload_ok


async def async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    coordinators = hass.data[DOMAIN][entry.entry_id]

    new_interval = entry.options.get("scan_interval", DEFAULT_SCAN_INTERVAL)
    titan_count = entry.data.get(CONF_TITAN_COUNT, 1)
    override = entry.data.get(CONF_OVERRIDE_RESPONSIBILITY, False)

    max_abs = titan_count * MAX_ABS_PER_TITAN

    for coordinator in coordinators.values():
        coordinator.update_interval = timedelta(seconds=new_interval)

        if override:
            charge = entry.options.get(
                DEFAULT_MAX_CHARGE_POWER,
                titan_count * CHARGE_PER_TITAN,
            )
            discharge = entry.options.get(
                DEFAULT_MAX_DISCHARGE_POWER,
                titan_count * DISCHARGE_PER_TITAN,
            )

            coordinator.max_charge_power = int(min(int(charge), int(max_abs)))
            coordinator.max_discharge_power = int(min(int(discharge), int(max_abs)))

        else:
            coordinator.max_charge_power = titan_count * CHARGE_PER_TITAN
            coordinator.max_discharge_power = titan_count * DISCHARGE_PER_TITAN

    _LOGGER.info(
        "Izypower Titan options updated — scan_interval=%ss, charge=%sW, discharge=%sW",
        new_interval,
        coordinator.max_charge_power,
        coordinator.max_discharge_power,
        max_abs,
    )