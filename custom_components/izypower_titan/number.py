from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_CONNECTION_MODE, CONNECTION_MODE_LABELS, CONTROL,CLUSTER_ROLE, CLUSTER_SLAVE

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinators = hass.data[DOMAIN][entry.entry_id]

    mode = entry.data.get(CONF_CONNECTION_MODE)
    mode_label = CONNECTION_MODE_LABELS.get(mode)

    cluster = entry.data.get("cluster", {})
    master_ip = cluster.get("master")

    entities = []

    for coordinator in coordinators.values():
        if coordinator.host != master_ip:
            continue

        candidates = [
            IzypowerChargePowerNumber(coordinator),
            IzypowerChargeSocLimitNumber(coordinator),
            IzypowerCloudMaxPowerNumber(coordinator, True, "Intelligent Charge Limit"),
            IzypowerCloudMaxPowerNumber(coordinator, False, "Intelligent Discharge Limit"),
        ]

        for entity in candidates:
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


"""
class IzypowerDischargePowerNumber(IzypowerBaseNumber):
    profile = "common"
    Puissance de décharge à utiliser quand on appuie sur le bouton Charge.

    _attr_native_step = 50
    _attr_native_unit_of_measurement = "W"

    def __init__(self, coordinator):
        super().__init__(coordinator, "discharge_power", "G Discharge power")

        self._attr_native_min_value = 0
        self._attr_native_max_value = float(
            coordinator.config_entry.options.get("max_discharge_power",  coordinator.max_discharge_power)
        )

        if self._value is None:
            self._value = min(500.0, self._attr_native_max_value)
"""


class IzypowerChargeSocLimitNumber(IzypowerBaseNumber):
    profile = "common"

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
