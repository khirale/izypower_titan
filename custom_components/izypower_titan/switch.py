from __future__ import annotations

import logging

from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.core import callback

from .const import DOMAIN, CONF_CONNECTION_MODE, CONNECTION_MODE_LABELS, CONTROL, ENTITY_SCOPE_UNIT

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
            IzypowerTitanRegisterOffGridSwitch(coordinator),
            IzypowerTitanRegisterLEDSwitch(coordinator),
        ]

        for entity in candidates:
            if CONTROL != "selected":
                entities.append(entity)
            else:
                if entity.profile == "common":
                    entities.append(entity)
                elif entity.profile == mode_label:
                    entities.append(entity)

    async_add_entities(entities)


class IzypowerTitanRegisterOffGridSwitch(CoordinatorEntity, SwitchEntity):
    profile = "common"
    scope = ENTITY_SCOPE_UNIT
    
    _attr_has_entity_name = True

    def __init__(self, coordinator):
        super().__init__(coordinator)
        
        host = coordinator.host
        self._attr_unique_id = f"{DOMAIN}_{host}_register_off_grid"
        self._attr_name = "Off-Grid"
        self._attr_device_info = coordinator.device_info
        
        self._optimistic_state = None
        
    @property
    def is_on(self) -> bool:
        if self._optimistic_state is not None:
            return self._optimistic_state
        
        data = self.coordinator.data or {}
        raw_value = data.get("680")
        
        if raw_value is None:
            return False
        
        try:
            return int(float(raw_value)) == 1
        except (TypeError, ValueError):
            _LOGGER.warning("Invalid value for sensor 680: %s", raw_value)
            return False

    async def async_turn_on(self, **kwargs) -> None:
        _LOGGER.info("Turning ON off_grid on %s", self.coordinator.host)
        
        try:
            self._optimistic_state = True
            self.async_write_ha_state()
            
            await self.coordinator.api.async_set_register_off_grid(1)
            await self.coordinator.async_request_refresh()
            
        except Exception as err:
            self._optimistic_state = None
            self.async_write_ha_state()
            _LOGGER.error("Failed to turn ON off_grid: %s", err)
            raise

    async def async_turn_off(self, **kwargs) -> None:
        _LOGGER.info("Turning OFF off_grid on %s", self.coordinator.host)
        
        try:
            self._optimistic_state = False
            self.async_write_ha_state()
            
            await self.coordinator.api.async_set_register_off_grid(0)
            await self.coordinator.async_request_refresh()
            
        except Exception as err:
            self._optimistic_state = None
            self.async_write_ha_state()
            _LOGGER.error("Failed to turn OFF off_grid: %s", err)
            raise

    @callback
    def _handle_coordinator_update(self) -> None:
        data = self.coordinator.data or {}
        raw_value = data.get("680")
        
        if raw_value is not None:
            try:
                sensor_state = int(float(raw_value)) == 1
                
                if self._optimistic_state is not None:
                    if self._optimistic_state == sensor_state:
                        _LOGGER.debug(
                            "Sensor 680 confirmed state %s, exiting optimistic mode",
                            "ON" if sensor_state else "OFF"
                        )
                        self._optimistic_state = None
                    else:
                        _LOGGER.debug(
                            "Sensor 680 not yet updated (expected %s, got %s), staying optimistic",
                            "ON" if self._optimistic_state else "OFF",
                            "ON" if sensor_state else "OFF"
                        )
                        return
            except (TypeError, ValueError):
                pass
        
        super()._handle_coordinator_update()

    @property
    def extra_state_attributes(self):
        return {
            "optimistic": self._optimistic_state is not None,
            "sensor_680_raw": self.coordinator.data.get("680") if self.coordinator.data else None,
        }

    @property
    def icon(self) -> str:
        if self.is_on:
            return "mdi:power-plug-outline"
        else:
            return "mdi:power-plug-off-outline"


class IzypowerTitanRegisterLEDSwitch(CoordinatorEntity, SwitchEntity):
    profile = "common"
    scope = ENTITY_SCOPE_UNIT
    
    _attr_has_entity_name = True

    def __init__(self, coordinator):
        super().__init__(coordinator)
        
        host = coordinator.host
        self._attr_unique_id = f"{DOMAIN}_{host}_leds_control"
        self._attr_name = "LEDs Control"
        self._attr_device_info = coordinator.device_info
        
        self._optimistic_state = None
        
    @property
    def is_on(self) -> bool:
        if self._optimistic_state is not None:
            return self._optimistic_state
        
        data = self.coordinator.data or {}
        raw_value = data.get("7171")
        
        if raw_value is None:
            return False
        
        try:
            return int(float(raw_value)) == 1
        except (TypeError, ValueError):
            _LOGGER.warning("Invalid value for sensor 7171: %s", raw_value)
            return False

    async def async_turn_on(self, **kwargs) -> None:
        _LOGGER.info("Turning ON LEDs on %s", self.coordinator.host)
        
        try:
            self._optimistic_state = True
            self.async_write_ha_state()
            
            await self.coordinator.api.async_set_register_led(1)
            await self.coordinator.async_request_refresh()
            
        except Exception as err:
            self._optimistic_state = None
            self.async_write_ha_state()
            _LOGGER.error("Failed to turn ON LEDs: %s", err)
            raise

    async def async_turn_off(self, **kwargs) -> None:
        _LOGGER.info("Turning OFF LEDs on %s", self.coordinator.host)
        
        try:
            self._optimistic_state = False
            self.async_write_ha_state()
            
            await self.coordinator.api.async_set_register_led(0)
            await self.coordinator.async_request_refresh()
            
        except Exception as err:
            self._optimistic_state = None
            self.async_write_ha_state()
            _LOGGER.error("Failed to turn OFF LEDs: %s", err)
            raise

    @callback
    def _handle_coordinator_update(self) -> None:
        data = self.coordinator.data or {}
        raw_value = data.get("7171")
        
        if raw_value is not None:
            try:
                sensor_state = int(float(raw_value)) == 1
                
                if self._optimistic_state is not None:
                    if self._optimistic_state == sensor_state:
                        _LOGGER.debug(
                            "Sensor 7171 confirmed state %s, exiting optimistic mode",
                            "ON" if sensor_state else "OFF"
                        )
                        self._optimistic_state = None
                    else:
                        _LOGGER.debug(
                            "Sensor 7171 not yet updated (expected %s, got %s), staying optimistic",
                            "ON" if self._optimistic_state else "OFF",
                            "ON" if sensor_state else "OFF"
                        )
                        return
            except (TypeError, ValueError):
                pass
        
        super()._handle_coordinator_update()

    @property
    def extra_state_attributes(self):
        return {
            "optimistic": self._optimistic_state is not None,
            "sensor_7171_raw": self.coordinator.data.get("7171") if self.coordinator.data else None,
        }
        
    @property
    def icon(self) -> str:
        if self.is_on:
            return "mdi:led-strip"
        else:
            return "mdi:led-strip-variant-off"