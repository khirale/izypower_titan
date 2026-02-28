from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError

from .const import (
    DOMAIN, 
    CONF_CONNECTION_MODE, 
    CONNECTION_MODE_LABELS, 
    CONTROL, 
    ENTITY_SCOPE_CLUSTER, 
    ENTITY_SCOPE_UNIT,
    SOC_SECURITY_MIN,
    SOC_SECURITY_MAX,
    SOC_SECURITY_STEP,
)
from .utils import is_meter_connected

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinators = hass.data[DOMAIN][entry.entry_id]

    mode = entry.data.get(CONF_CONNECTION_MODE)
    mode_label = CONNECTION_MODE_LABELS.get(mode)

    cluster = entry.data.get("cluster", {})
    master_ip = cluster.get("master")

    entities = []

    for coordinator in coordinators.values():
        candidates = [
            IzypowerChargePowerNumber(coordinator),
            IzypowerChargeSocLimitNumber(coordinator),
            IzypowerCloudMaxPowerNumber(coordinator, True, "Intelligent Charge Limit"),
            IzypowerCloudMaxPowerNumber(coordinator, False, "Intelligent Discharge Limit"),
            IzypowerSocSecurityNumber(coordinator),
            IzypowerMaxPowerNumber(coordinator),
            IzypowerMaxDischargePowerNumber(coordinator),
        ]

        for entity in candidates:
            if hasattr(entity, 'scope') and entity.scope == ENTITY_SCOPE_CLUSTER:
                if coordinator.host != master_ip:
                    continue

            if CONTROL != "selected":
                entities.append(entity)
                continue
            if entity.profile == "common":
                entities.append(entity)
            elif entity.profile == mode_label:
                entities.append(entity)

    async_add_entities(entities, update_before_add=False)


class IzypowerBaseNumber(NumberEntity, RestoreEntity):

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_mode = NumberMode.SLIDER
    
    profile: str = "common"
    scope: str = ENTITY_SCOPE_CLUSTER

    def __init__(self, coordinator, unique_suffix: str, name: str):
        self.coordinator = coordinator
        entry = coordinator.config_entry
        host = coordinator.host

        self._attr_unique_id = f"{DOMAIN}_{host}_{unique_suffix}"
        self._attr_name = name

        self._attr_device_info = coordinator.device_info

        self._value: float | None = None

    @property
    def native_value(self) -> float | None:
        return self._value

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        last = await self.async_get_last_state()
        if last and last.state not in (None, "unknown", "unavailable"):
            try:
                self._value = float(last.state)
            except (ValueError, TypeError):
                _LOGGER.debug("Impossible de restaurer %s (last=%s)", self.entity_id, last.state)

    async def async_set_native_value(self, value: float) -> None:
        self._value = float(value)
        self.async_write_ha_state()


class IzypowerChargePowerNumber(IzypowerBaseNumber):
    profile = "common"
    scope = ENTITY_SCOPE_CLUSTER

    _attr_native_step = 50
    _attr_native_unit_of_measurement = "W"

    def __init__(self, coordinator):
        super().__init__(coordinator, "charge_discharge_power", "Charge/Discharge power")

        self._attr_native_min_value = 0
        self._attr_native_max_value = float(
            coordinator.config_entry.options.get("max_charge_power", coordinator.max_charge_power)
        )

        if self._value is None:
            self._value = min(500.0, self._attr_native_max_value)


class IzypowerChargeSocLimitNumber(IzypowerBaseNumber):
    profile = "MR1"
    scope = ENTITY_SCOPE_CLUSTER

    _attr_native_min_value = 0
    _attr_native_max_value = 100
    _attr_native_step = 5
    _attr_native_unit_of_measurement = "%"

    def __init__(self, coordinator):
        super().__init__(coordinator, "charge_soc_limit", "Charge SOC Max")

        if self._value is None:
            self._value = 100.0


class IzypowerCloudMaxPowerNumber(CoordinatorEntity, NumberEntity, RestoreEntity):
    profile = "Smart IA"
    scope = ENTITY_SCOPE_CLUSTER 

    _attr_has_entity_name = True
    _attr_mode = NumberMode.SLIDER
    _attr_native_step = 50
    _attr_native_unit_of_measurement = "W"
    _attr_should_poll = False

    def __init__(self, coordinator, is_charge: bool, name: str):
        super().__init__(coordinator)

        self.is_charge = is_charge
        entry = coordinator.config_entry
        host = coordinator.host

        self._attr_name = name
        suffix = "charge" if is_charge else "discharge"
        self._attr_unique_id = f"{DOMAIN}_{host}_cloud_{suffix}_limit"
        self._attr_device_info = coordinator.device_info

        if is_charge:
            self._max_value = float(
                entry.options.get(
                    "max_charge_power",
                    coordinator.max_charge_power,
                )
            )
        else:
            self._max_value = float(
                entry.options.get(
                    "max_discharge_power",
                    coordinator.max_discharge_power,
                )
            )

        self._attr_native_min_value = 0.0
        self._attr_native_max_value = self._max_value

        self._value: float | None = None

    @property
    def native_value(self) -> float | None:
        return self._value

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        last = await self.async_get_last_state()
        if last and last.state not in (None, "unknown", "unavailable"):
            try:
                self._value = float(last.state)
            except (ValueError, TypeError):
                pass
        else:
            self._value = self._max_value

        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        device_sn = self.coordinator.serial_number

        if not device_sn:
            _LOGGER.error("Serial Number introuvable")
            return

        target = int(value)

        try:
            if self.is_charge:
                await self.coordinator.async_cloud_set_charge_power(
                    device_sn, target
                )
            else:
                await self.coordinator.async_cloud_set_discharge_power(
                    device_sn, target
                )

            self._value = float(target)
            self.async_write_ha_state()

        except Exception as err:
            _LOGGER.error("Erreur Cloud : %s", err)


class IzypowerSocSecurityNumber(CoordinatorEntity, NumberEntity, RestoreEntity):
    #_attr_entity_picture = "/local/battery_red.png"
    profile = "common"
    scope = ENTITY_SCOPE_CLUSTER

    _attr_has_entity_name = True
    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = SOC_SECURITY_MIN
    _attr_native_max_value = SOC_SECURITY_MAX
    _attr_native_step = SOC_SECURITY_STEP
    _attr_native_unit_of_measurement = "%"
    _attr_should_poll = False

    def __init__(self, coordinator):
        super().__init__(coordinator)

        host = coordinator.host
        self._attr_unique_id = f"{DOMAIN}_{host}_soc_security"
        self._attr_name = "SOC Security (ESP)"
        self._attr_device_info = coordinator.device_info

        self._value: float | None = None
        self._pending_value: float | None = None

    @property
    def native_value(self) -> float | None:
        return self._value

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        data = self.coordinator.data or {}
        raw_value = data.get("6105")

        if raw_value is not None:
            try:
                value = float(raw_value)
                if SOC_SECURITY_MIN <= value <= SOC_SECURITY_MAX:
                    self._value = value
                    _LOGGER.debug(
                        "SOC Security initialized from sensor 6105: %s%%",
                        self._value
                    )
                else:
                    _LOGGER.debug(
                        "Sensor 6105 value %s out of range (%s-%s), waiting for next update",
                        value,
                        SOC_SECURITY_MIN,
                        SOC_SECURITY_MAX
                    )
            except (ValueError, TypeError):
                _LOGGER.debug("Cannot parse sensor 6105 value: %s", raw_value)

        self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Update value from sensor 6105, respecting optimistic mode."""
        data = self.coordinator.data or {}
        raw_value = data.get("6105")

        if raw_value is not None:
            try:
                sensor_value = float(raw_value)
                
                if not (SOC_SECURITY_MIN <= sensor_value <= SOC_SECURITY_MAX):
                    super()._handle_coordinator_update()
                    return
                
                if self._pending_value is not None:
                    if abs(sensor_value - self._pending_value) < 0.1:
                        _LOGGER.debug(
                            "SOC Security confirmed by sensor 6105: %s%%",
                            sensor_value
                        )
                        self._pending_value = None
                        self._value = sensor_value
                    else:
                        _LOGGER.debug(
                            "SOC Security waiting for confirmation: local=%s%%, sensor=%s%%",
                            self._pending_value,
                            sensor_value
                        )
                        super()._handle_coordinator_update()
                        return
                
                else:
                    if self._value != sensor_value:
                        self._value = sensor_value
                        _LOGGER.info(
                            "SOC Security updated from external change (sensor 6105): %s%%",
                            self._value
                        )
                        
            except (ValueError, TypeError) as err:
                _LOGGER.debug("Cannot parse sensor 6105 value: %s (%s)", raw_value, err)

        super()._handle_coordinator_update()

    async def async_set_native_value(self, value: float) -> None:
        from . import execute_on_cluster_coordinators
        
        old_value = self._value

        self._pending_value = value
        self._value = value
        self.async_write_ha_state()

        try:
            await execute_on_cluster_coordinators(
                self.hass,
                self.coordinator,
                "async_set_soc_security_register",
                int(value),
                int(old_value) if old_value is not None else None,
            )
            

        except Exception as err:
            self._value = old_value
            self._pending_value = None
            self.async_write_ha_state()
            _LOGGER.error("Failed to set SOC security: %s", err)
            raise


class IzypowerMaxPowerNumber(CoordinatorEntity, NumberEntity, RestoreEntity):
    profile = "MR1"
    scope = ENTITY_SCOPE_CLUSTER

    _attr_has_entity_name = True
    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = 50
    _attr_native_step = 50
    _attr_native_unit_of_measurement = "W"
    _attr_should_poll = False

    def __init__(self, coordinator):
        super().__init__(coordinator)

        entry = coordinator.config_entry
        host = coordinator.host

        self._attr_unique_id = f"{DOMAIN}_{host}_max_power"
        self._attr_name = "Max Charge Power"
        self._attr_device_info = coordinator.device_info

        self._attr_native_max_value = float(
            entry.options.get(
                "max_charge_power",
                coordinator.max_charge_power,
            )
        )

        self._value: float | None = None

    @property
    def native_value(self) -> float | None:
        return self._value

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        last = await self.async_get_last_state()
        if last and last.state not in (None, "unknown", "unavailable"):
            try:
                self._value = float(last.state)
            except (ValueError, TypeError):
                pass
        else:
            self._value = self._attr_native_max_value

        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        if not is_meter_connected(self.coordinator):
            raise HomeAssistantError(
                "Mauvaise configuration de l'intégration - Veuillez utiliser le bon choix de meter"
            )
        
        from . import execute_on_cluster_coordinators
        
        old_value = self._value

        self._value = value
        self.async_write_ha_state()

        try:
            await execute_on_cluster_coordinators(
                self.hass,
                self.coordinator,
                "async_set_max_power_register",
                int(value),
                int(old_value) if old_value is not None else None,
            )

        except Exception as err:
            self._value = old_value
            self.async_write_ha_state()
            _LOGGER.error("Failed to set Max Power: %s", err)
            raise


class IzypowerMaxDischargePowerNumber(CoordinatorEntity, NumberEntity, RestoreEntity):
    profile = "MR1"
    scope = ENTITY_SCOPE_CLUSTER

    _attr_has_entity_name = True
    _attr_mode = NumberMode.SLIDER
    _attr_native_min_value = 100
    _attr_native_step = 50
    _attr_native_unit_of_measurement = "W"
    _attr_should_poll = False

    def __init__(self, coordinator):
        super().__init__(coordinator)

        entry = coordinator.config_entry
        host = coordinator.host

        self._attr_unique_id = f"{DOMAIN}_{host}_max_discharge_power"
        self._attr_name = "Max Discharge Power"
        self._attr_device_info = coordinator.device_info

        from .const import CONF_TITAN_COUNT, CONF_OVERRIDE_RESPONSIBILITY, DISCHARGE_PER_TITAN, MAX_ABS_PER_TITAN
        
        override = entry.data.get(CONF_OVERRIDE_RESPONSIBILITY, False)
        
        if override:
            self._attr_native_max_value = float(MAX_ABS_PER_TITAN)  # 2400W
        else:
            self._attr_native_max_value = float(DISCHARGE_PER_TITAN)  # 800W

        self._value: float | None = None

    @property
    def native_value(self) -> float | None:
        return self._value

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        last = await self.async_get_last_state()
        if last and last.state not in (None, "unknown", "unavailable"):
            try:
                self._value = float(last.state)
            except (ValueError, TypeError):
                pass
        else:
            self._value = self._attr_native_max_value

        self.async_write_ha_state()

    async def async_set_native_value(self, value: float) -> None:
        if not is_meter_connected(self.coordinator):
            raise HomeAssistantError(
                "Mauvaise configuration de l'intégration - Veuillez utiliser le bon choix de meter"
            )
        
        from . import execute_on_cluster_coordinators
        
        old_value = self._value

        self._value = value
        self.async_write_ha_state()

        try:
            await execute_on_cluster_coordinators(
                self.hass,
                self.coordinator,
                "async_set_max_discharge_power_register",
                int(value),
                int(old_value) if old_value is not None else None,
            )

        except Exception as err:
            self._value = old_value
            self.async_write_ha_state()
            _LOGGER.error("Failed to set Max Discharge Power: %s", err)
            raise
