from __future__ import annotations

import logging
from typing import Any
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    PLATFORMS,
    CONF_TITAN_COUNT,
    CONF_OVERRIDE_RESPONSIBILITY,
    CHARGE_PER_TITAN,
    DISCHARGE_PER_TITAN,
    CONF_CONNECTION_MODE,
    MODE_LOCAL,
    MODE_CLOUD,
    MAX_ABS_PER_TITAN,
    SOC_SECURITY_MIN,
    SOC_SECURITY_MAX,
)
from .coordinator import IzypowerTitanCoordinator
from .cloud_api import IzyCloudAPI
from .storage import TitanCalibrationStorage

_LOGGER = logging.getLogger(__name__)

SERVICES = [
    "charge",
    "discharge",
    "stop",
    "set_realtime_mode",
    "set_intelligent_mode",
    "set_selfconsumed_mode",
    "cloud_charge_manual",
    "cloud_discharge_manual",
    "set_cloud_max_charge",
    "set_cloud_max_discharge",
    "set_cloud_intelligent_mode",
    "set_cloud_standby_mode",
    "set_register_off_grid",
    "set_register_led",
    "set_soc_security",
    "set_max_power",
    "set_max_discharge_power",
    "cluster_rebalance",
]

STALE_SUFFIXES_BY_MODE = {
    MODE_CLOUD: [
        "realtime",
        "stop",
        "self-consumed mode",
        "charge",
        "discharge",
        "charge_soc_limit",
        "max_power",
        "max_discharge_power",
    ],
    MODE_LOCAL: [
        "cloud_charge",
        "cloud_discharge",
        "cloud_auto",
        "standby mode",
        "cloud_charge_limit",
        "cloud_discharge_limit",
        "cloud_connectivity",
    ],
}


def _async_cleanup_stale_entities(hass: HomeAssistant, entry: ConfigEntry) -> None:
    mode = entry.data.get(CONF_CONNECTION_MODE)
    stale_suffixes = STALE_SUFFIXES_BY_MODE.get(mode)
    if not stale_suffixes:
        return

    cluster = entry.data.get("cluster", {})
    hosts = [cluster.get("master")] + cluster.get("slaves", [])

    stale_unique_ids = {
        f"{DOMAIN}_{host}_{suffix}"
        for host in hosts
        if host
        for suffix in stale_suffixes
    }

    ent_reg = er.async_get(hass)
    removed = 0
    for reg_entry in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
        if reg_entry.unique_id in stale_unique_ids:
            _LOGGER.info(
                "Purge entité orpheline (changement de mode → %s) : %s",
                mode, reg_entry.entity_id,
            )
            ent_reg.async_remove(reg_entry.entity_id)
            removed += 1

    if removed:
        _LOGGER.info("%d entité(s) de l'ancien profil supprimée(s) du registre", removed)

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


def build_max_power_schema(max_power: int) -> vol.Schema:
    return vol.Schema({
        vol.Required("value"): vol.All(cv.positive_int, vol.Range(min=50, max=max_power)),
        vol.Optional("device_id"): cv.string,
    })


def build_max_discharge_power_schema(max_power: int) -> vol.Schema:
    return vol.Schema({
        vol.Required("value"): vol.All(cv.positive_int, vol.Range(min=100, max=max_power)),
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

SERVICE_REGISTER_OFF_GRID_SCHEMA = vol.Schema({
    vol.Required("value"): vol.All(cv.positive_int, vol.Range(min=0, max=1)),
    vol.Optional("device_id"): cv.string,
})

SERVICE_REGISTER_LED_SCHEMA = vol.Schema({
    vol.Required("value"): vol.All(cv.positive_int, vol.Range(min=0, max=1)),
    vol.Optional("device_id"): cv.string,
})

SERVICE_SOC_SECURITY_SCHEMA = vol.Schema({
    vol.Required("value"): vol.All(cv.positive_int, vol.Range(min=SOC_SECURITY_MIN, max=SOC_SECURITY_MAX)),
    vol.Optional("device_id"): cv.string,
})

SERVICE_CLUSTER_REBALANCE_SCHEMA = vol.Schema({
    vol.Optional("soc_security"): vol.All(cv.positive_int, vol.Range(min=SOC_SECURITY_MIN, max=SOC_SECURITY_MAX)),
    vol.Optional("max_charge_power"): cv.positive_int,
    vol.Optional("max_discharge_power"): cv.positive_int,
    vol.Optional("device_id"): cv.string,
})


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})

    try:
        titan_count = int(entry.data.get(CONF_TITAN_COUNT, 1))
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

        shared_cloud_api = IzyCloudAPI(
            username=entry.data.get("username", ""),
            password=entry.data.get("password", ""),
            session=async_get_clientsession(hass),
        )

        for host in hosts:
            coordinator = IzypowerTitanCoordinator(
                hass,
                entry,
                host=host,
                max_charge=final_max_charge,
                max_discharge=final_max_discharge,
                cloud_api=shared_cloud_api,
            )

            calibration_storage = TitanCalibrationStorage(hass, entry.entry_id, host)
            await calibration_storage.async_load()
            coordinator.calibration_storage = calibration_storage

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

        _async_cleanup_stale_entities(hass, entry)

        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
        entry.async_on_unload(entry.add_update_listener(async_update_listener))

        if not hass.services.has_service(DOMAIN, "charge"):
            await async_register_services(hass)

        _LOGGER.info(
            "Izypower Titan setup complete – %s Titans (%s)",
            len(hosts),
            ", ".join(hosts),
        )

        return True

    except Exception:
        if entry.entry_id in hass.data.get(DOMAIN, {}):
            del hass.data[DOMAIN][entry.entry_id]
        raise


async def execute_on_cluster_coordinators(
    hass: HomeAssistant,
    coordinator: "IzypowerTitanCoordinator",
    command_name: str,
    value: Any,
    rollback_value: Any | None = None,
) -> None:

    entry_id = coordinator.config_entry.entry_id
    coordinators_dict = hass.data[DOMAIN].get(entry_id, {})

    if not coordinators_dict:
        raise HomeAssistantError(f"No coordinators found for entry {entry_id}")

    coordinator_list = list(coordinators_dict.values())

    unreachable = [c.host for c in coordinator_list if not c.last_update_success]
    if unreachable:
        raise HomeAssistantError(
            f"Cluster command '{command_name}' annulé : "
            f"Titan(s) injoignable(s) — {', '.join(unreachable)}"
        )

    _LOGGER.debug(
        "Executing cluster command '%s' on %d coordinator(s)",
        command_name,
        len(coordinator_list)
    )

    successful_coordinators = []

    try:
        for coord in coordinator_list:
            command_method = getattr(coord, command_name)
            
            _LOGGER.debug(
                "Executing %s(%s) on coordinator %s",
                command_name,
                value,
                coord.host
            )
            
            await command_method(value)
            successful_coordinators.append(coord)
            
        _LOGGER.info(
            "Cluster command '%s' executed successfully on %d coordinator(s)",
            command_name,
            len(successful_coordinators)
        )

    except Exception as err:
        _LOGGER.error(
            "Cluster command '%s' failed on coordinator %s after %d successful execution(s). Error: %s",
            command_name,
            coord.host if coord else "unknown",
            len(successful_coordinators),
            err
        )

        if rollback_value is not None and successful_coordinators:
            _LOGGER.warning(
                "Attempting rollback to value %s on %d coordinator(s)",
                rollback_value,
                len(successful_coordinators)
            )
            
            for rollback_coord in successful_coordinators:
                try:
                    rollback_method = getattr(rollback_coord, command_name)
                    await rollback_method(rollback_value)
                    _LOGGER.debug(
                        "Rollback successful on coordinator %s",
                        rollback_coord.host
                    )
                except Exception as rollback_err:
                    _LOGGER.error(
                        "Rollback failed on coordinator %s: %s",
                        rollback_coord.host,
                        rollback_err
                    )

        raise HomeAssistantError(
            f"Cluster command '{command_name}' failed: {err}"
        ) from err


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

        device_id = call.data.get("device_id")

        entity_id = call.data.get("entity_id")
        if entity_id:
            entity_reg = er.async_get(hass)
            entity = entity_reg.async_get(entity_id)

            if not entity or not entity.device_id:
                raise HomeAssistantError("entity_id invalide ou non associé à un device")

            device_id = entity.device_id
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
                raise HomeAssistantError("Ce device n'est pas un Titan Izypower")

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
        if not coordinator:
            return
        
        power = call.data["power"]
        soc_limit = call.data.get("soc_limit", 100)
        max_p = coordinator.max_charge_power
        await coordinator.api.async_charge(power, soc_limit, max_p)
        await coordinator.async_request_refresh()

    async def discharge(call: ServiceCall):
        coordinator = await get_coordinator_from_call(call)
        if not coordinator:
            return
        
        power = call.data["power"]
        soc_limit = call.data.get("soc_limit", 5)
        max_p = coordinator.max_discharge_power
        await coordinator.api.async_discharge(power, soc_limit, max_p)
        await coordinator.async_request_refresh()

    async def stop(call: ServiceCall):
        coordinator = await get_coordinator_from_call(call)
        if not coordinator:
            return
        
        await coordinator.api.async_stop()
        await coordinator.async_request_refresh()

    async def set_realtime_mode(call: ServiceCall):
        coordinator = await get_coordinator_from_call(call)
        if not coordinator:
            return
        
        await coordinator.api.async_set_realtime_mode()
        await coordinator.async_request_refresh()

    async def set_intelligent_mode(call: ServiceCall):
        coordinator = await get_coordinator_from_call(call)
        if coordinator:
            await coordinator.api.async_set_working_mode(4) 
            await coordinator.async_request_refresh()

    async def set_selfconsumed_mode(call: ServiceCall):
        coordinator = await get_coordinator_from_call(call)
        if not coordinator:
            return
        
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

    async def cloud_discharge_manual(call: ServiceCall):
        coordinator = await get_coordinator_from_call(call)
        if not coordinator: return
        sn = coordinator.serial_number
        power = call.data.get("power", 800)
        if sn:
            _LOGGER.info("Appel Décharge Cloud pour SN %s à %s W", sn, power)
            await coordinator.cloud_api.async_cloud_manual_discharge(sn, power)
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

    
    async def set_register_off_grid(call: ServiceCall):
        coordinator = await get_coordinator_from_call(call)
        if not coordinator: return
        value = call.data["value"]
        await coordinator.api.async_set_register_off_grid(value)
        await coordinator.async_request_refresh()

    async def set_register_led(call: ServiceCall):
        coordinator = await get_coordinator_from_call(call)
        if not coordinator: return
        value = call.data["value"]
        await coordinator.api.async_set_register_led(value)
        await coordinator.async_request_refresh()

    async def set_soc_security(call: ServiceCall):
        coordinator = await get_coordinator_from_call(call)
        if not coordinator:
            return

        value = call.data["value"]

        rollback_value = None
        try:
            raw = coordinator.data.get("6105")
            if raw is not None:
                rollback_value = int(float(raw))
        except Exception:
            pass

        await execute_on_cluster_coordinators(
            call.hass,
            coordinator,
            "async_set_soc_security_register",
            value,
            rollback_value=rollback_value,
        )
        
        entry_id = coordinator.config_entry.entry_id
        coordinators = call.hass.data[DOMAIN].get(entry_id, {})
        
        for coord in coordinators.values():
            await coord.async_request_refresh()

    async def set_max_power(call: ServiceCall):
        coordinator = await get_coordinator_from_call(call)
        if not coordinator:
            return

        value = call.data["value"]

        rollback_value = None
        try:
            raw = coordinator.data.get("11009")
            if raw is not None:
                rollback_value = int(float(raw))
        except Exception:
            pass

        await execute_on_cluster_coordinators(
            call.hass,
            coordinator,
            "async_set_max_power_register",
            value,
            rollback_value=rollback_value,
        )
        
        entry_id = coordinator.config_entry.entry_id
        coordinators = call.hass.data[DOMAIN].get(entry_id, {})
        
        for coord in coordinators.values():
            await coord.async_request_refresh()

    async def set_max_discharge_power(call: ServiceCall):
        coordinator = await get_coordinator_from_call(call)
        if not coordinator:
            return

        value = call.data["value"]

        rollback_value = None
        try:
            raw = coordinator.data.get("11011")
            if raw is not None:
                rollback_value = int(float(raw))
        except Exception:
            pass

        await execute_on_cluster_coordinators(
            call.hass,
            coordinator,
            "async_set_max_discharge_power_register",
            value,
            rollback_value=rollback_value,
        )

        entry_id = coordinator.config_entry.entry_id
        coordinators = call.hass.data[DOMAIN].get(entry_id, {})

        for coord in coordinators.values():
            await coord.async_request_refresh()

    async def cluster_rebalance(call: ServiceCall):
        coordinator = await get_coordinator_from_call(call)
        if not coordinator:
            return

        soc = call.data.get("soc_security")
        max_c = call.data.get("max_charge_power")
        max_d = call.data.get("max_discharge_power")

        if soc is None and max_c is None and max_d is None:
            raise HomeAssistantError(
                "Au moins un paramètre requis : soc_security, max_charge_power ou max_discharge_power"
            )

        entry_id = coordinator.config_entry.entry_id
        coordinators = call.hass.data[DOMAIN].get(entry_id, {})

        errors: list[str] = []

        for coord in coordinators.values():
            if soc is not None:
                try:
                    await coord.async_set_soc_security_register(soc)
                except Exception as err:
                    errors.append(f"{coord.host}/soc_security={soc}: {err}")

            if max_c is not None:
                try:
                    await coord.async_set_max_power_register(max_c)
                except Exception as err:
                    errors.append(f"{coord.host}/max_charge_power={max_c}: {err}")

            if max_d is not None:
                try:
                    await coord.async_set_max_discharge_power_register(max_d)
                except Exception as err:
                    errors.append(f"{coord.host}/max_discharge_power={max_d}: {err}")

        for coord in coordinators.values():
            await coord.async_request_refresh()

        if errors:
            _LOGGER.warning(
                "Cluster rebalance terminé avec %d erreur(s) : %s",
                len(errors), errors,
            )
            raise HomeAssistantError(
                f"Rebalance partiellement échoué ({len(errors)} erreur(s)) — voir logs"
            )

        _LOGGER.info(
            "Cluster rebalance OK sur %d Titan(s) (soc=%s, max_c=%s, max_d=%s)",
            len(coordinators), soc, max_c, max_d,
        )

    abs_max = 3 * MAX_ABS_PER_TITAN

    charge_schema = build_charge_schema(abs_max)
    discharge_schema = build_discharge_schema(abs_max)
    max_power_schema = build_max_power_schema(abs_max)
    max_discharge_power_schema = build_max_discharge_power_schema(abs_max)

    hass.services.async_register(DOMAIN, "charge", charge, schema=charge_schema)
    hass.services.async_register(DOMAIN, "discharge", discharge, schema=discharge_schema)
    hass.services.async_register(DOMAIN, "stop", stop, schema=SERVICE_DEVICE_SCHEMA)
    hass.services.async_register(DOMAIN, "set_realtime_mode", set_realtime_mode, schema=SERVICE_DEVICE_SCHEMA)
    hass.services.async_register(DOMAIN, "set_intelligent_mode", set_intelligent_mode, schema=SERVICE_DEVICE_SCHEMA)
    hass.services.async_register(DOMAIN, "set_selfconsumed_mode", set_selfconsumed_mode, schema=SERVICE_DEVICE_SCHEMA)
    hass.services.async_register(DOMAIN, "cloud_charge_manual", cloud_charge_manual, schema=SERVICE_CLOUD_CHARGE_SCHEMA)
    hass.services.async_register(DOMAIN, "cloud_discharge_manual", cloud_discharge_manual, schema=SERVICE_CLOUD_DISCHARGE_SCHEMA)
    hass.services.async_register(DOMAIN, "set_cloud_max_charge", set_cloud_max_charge, schema=SERVICE_CLOUD_CHARGE_SCHEMA)
    hass.services.async_register(DOMAIN, "set_cloud_max_discharge", set_cloud_max_discharge, schema=SERVICE_CLOUD_DISCHARGE_SCHEMA)
    hass.services.async_register(DOMAIN, "set_cloud_intelligent_mode", set_cloud_intelligent_mode, schema=SERVICE_DEVICE_SCHEMA)
    hass.services.async_register(DOMAIN, "set_cloud_standby_mode", set_cloud_standby_mode, schema=SERVICE_DEVICE_SCHEMA)
    hass.services.async_register(DOMAIN, "set_register_off_grid", set_register_off_grid, schema=SERVICE_REGISTER_OFF_GRID_SCHEMA)
    hass.services.async_register(DOMAIN, "set_register_led", set_register_led, schema=SERVICE_REGISTER_LED_SCHEMA)
    hass.services.async_register(DOMAIN, "set_soc_security", set_soc_security, schema=SERVICE_SOC_SECURITY_SCHEMA)
    hass.services.async_register(DOMAIN, "set_max_power", set_max_power, schema=max_power_schema)
    hass.services.async_register(DOMAIN, "set_max_discharge_power", set_max_discharge_power, schema=max_discharge_power_schema)
    hass.services.async_register(DOMAIN, "cluster_rebalance", cluster_rebalance, schema=SERVICE_CLUSTER_REBALANCE_SCHEMA)


    _LOGGER.info("Izypower Titan services registered successfully.")

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    if DOMAIN not in hass.data or entry.entry_id not in hass.data[DOMAIN]:
        return True

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinators = hass.data[DOMAIN].pop(entry.entry_id)

        for coordinator in coordinators.values():
            await coordinator.async_shutdown()

        if not hass.data[DOMAIN]:
            for service in SERVICES:
                hass.services.async_remove(DOMAIN, service)

    return unload_ok


async def async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    _LOGGER.info("Izypower Titan options updated – reloading entry %s", entry.entry_id)
    await hass.config_entries.async_reload(entry.entry_id)
