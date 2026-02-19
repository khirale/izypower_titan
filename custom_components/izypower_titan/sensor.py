from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorEntityDescription,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.core import callback
from homeassistant.util import dt as dt_util
from dataclasses import dataclass, field
from typing import Any
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfPower,
    PERCENTAGE,
)
import logging

from .const import (
    CONF_CONNECTION_MODE,
    DOMAIN,
    ID_META,
    MODE_CLOUD,
    WORKING_MODE_MAPPING_LOCAL,
    WORKING_MODE_MAPPING_CLOUD,
)
from .utils import normalize_unit, map_device_class, map_state_class
from .sensor_link import async_setup_entry as async_setup_link_entry

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class IzypowerSensorEntityDescription(SensorEntityDescription):
    coefficient: float = 1.0
    state_mapping: dict[int, str] = field(default_factory=dict)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinators = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for coordinator in coordinators.values():
        for key, meta in ID_META.items():
            entities.append(
                IzypowerSensorEntity(
                    coordinator=coordinator,
                    description=IzypowerSensorEntityDescription(
                        key=str(key),
                        name=meta.get("name", f"TITAN - {key}"),
                        native_unit_of_measurement=(
                            UnitOfEnergy.KILO_WATT_HOUR
                            if meta.get("dev_class") == "energy"
                            else normalize_unit(meta.get("unit"))
                        ),
                        device_class=map_device_class(meta.get("dev_class")),
                        state_class=map_state_class(meta.get("state_class")),
                        coefficient=meta.get("coefficient", 1.0),
                        state_mapping=meta.get("state_mapping", {}),
                        entity_category=(
                            EntityCategory.DIAGNOSTIC
                            if meta.get("key") in ("alarm_code", "backup", "leds")
                            else None
                        ),
                    ),
                )
            )

        mode = entry.data.get(CONF_CONNECTION_MODE)

        entities.extend(
            [
                IzypowerOptionSensor(entry, coordinator, "max_charge_power", "Max Charge Power", "W"),
                IzypowerOptionSensor(entry, coordinator, "max_discharge_power", "Max Discharge Power", "W"),
                IzypowerConnectivitySensor(coordinator, "connectivity_status", "TITAN - Connectivity"),
                IzypowerConnectivityUptimeSensor(coordinator, "connectivity_uptime", "TITAN - Connectivity Uptime"),
            ]
        )

        if mode == MODE_CLOUD:
            entities.append(
                IzypowerCloudStatusSensor(coordinator, "cloud_status", "TITAN - Cloud Status")
            )

    async_add_entities(entities)
    await async_setup_link_entry(hass, entry, async_add_entities)

    _LOGGER.info("Création de %d entités Izypower Titan", len(entities))


class IzypowerSensorEntity(CoordinatorEntity, SensorEntity):

    _attr_has_entity_name = True

    def __init__(self, coordinator, description: IzypowerSensorEntityDescription):
        super().__init__(coordinator)
        self.entity_description = description

        host = coordinator.host
        self._attr_unique_id = f"{DOMAIN}_{host}_{description.key}"
        self._attr_device_info = coordinator.device_info

        if description.device_class == SensorDeviceClass.ENUM:
            if description.key == "7101":
                self._attr_options = list(
                    {"Unknown"}
                    | set(WORKING_MODE_MAPPING_LOCAL.values())
                    | set(WORKING_MODE_MAPPING_CLOUD.values())
                )
            else:
                self._attr_options = list(set(description.state_mapping.values()))

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        raw_value = data.get(self.entity_description.key)

        if self.entity_description.device_class == SensorDeviceClass.ENUM:
            if self.entity_description.key == "8100" and raw_value is None:
                raw_value = 0
            elif raw_value is None:
                return None

            try:
                raw_value = int(float(raw_value))
            except (TypeError, ValueError):
                return None

            if self.entity_description.key == "7101":
                mode = self.coordinator.config_entry.data.get(CONF_CONNECTION_MODE)
                mapping = (
                    WORKING_MODE_MAPPING_CLOUD
                    if mode == MODE_CLOUD
                    else WORKING_MODE_MAPPING_LOCAL
                )
                return mapping.get(raw_value, "Unknown")

            return self.entity_description.state_mapping.get(raw_value, str(raw_value))

        if raw_value is None:
            return None

        try:
            value = float(raw_value) * self.entity_description.coefficient
            if self.entity_description.device_class == SensorDeviceClass.ENERGY:
                raw_unit = ID_META.get(int(self.entity_description.key), {}).get("unit")
                if raw_unit == "Wh":
                    value = value / 1000.0

        except (TypeError, ValueError):
            return None

        if self.entity_description.key in ("11019", "11020"):
            if value == 9999:
                return 0
            return int(value)

        if self.entity_description.key == "0":
            try:
                return str(int(value))
            except (TypeError, ValueError):
                return str(raw_value)

        return value


class IzypowerOptionSensor(SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry, coordinator, option_key: str, name: str, unit: str):
        self.entry = entry
        self.coordinator = coordinator
        self.option_key = option_key
        host = coordinator.host

        self._attr_unique_id = f"{DOMAIN}_{host}_titan_{option_key}"
        self._attr_name = f"TITAN - {name}"
        self._attr_native_unit_of_measurement = unit
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self):
        return self.entry.options.get(self.option_key)


class IzypowerConnectivitySensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, key, name):
        super().__init__(coordinator)
        host = coordinator.host

        self._attr_unique_id = f"{DOMAIN}_{host}_connectivity"
        self._attr_name = name
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self):
        return "OK" if getattr(self.coordinator, "last_http_ok", False) else "KO"


class IzypowerConnectivityUptimeSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator, key, name):
        super().__init__(coordinator)
        host = coordinator.host

        self._attr_unique_id = f"{DOMAIN}_{host}_connectivity_uptime"
        self._attr_name = name
        self._attr_device_info = coordinator.device_info

        self._ok = 0
        self._total = 0
        self._day = None

    @callback
    def _handle_coordinator_update(self) -> None:
        today_str = dt_util.now().date().isoformat()

        if self._day is None:
            self._day = today_str

        if self._day != today_str:
            self._day = today_str
            self._ok = 0
            self._total = 0

        self._total += 1
        if getattr(self.coordinator, "last_http_ok", False):
            self._ok += 1

        super()._handle_coordinator_update()

    @property
    def native_value(self):
        if self._total == 0:
            return 100.0
        return round((self._ok / self._total) * 100.0, 2)

    @property
    def extra_state_attributes(self):
        return {
            "ok": self._ok,
            "total": self._total,
            "day": self._day,
        }


class IzypowerCloudStatusSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, key, name):
        super().__init__(coordinator)
        host = coordinator.host

        self._attr_unique_id = f"{DOMAIN}_{host}_cloud_connectivity"
        self._attr_name = name
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> str:
        cloud = getattr(self.coordinator, "cloud_api", None)
        return "Connected" if cloud and getattr(cloud, "token", None) else "Disconnected"

    @property
    def icon(self) -> str:
        return "mdi:cloud-check" if self.native_value == "Connected" else "mdi:cloud-off-outline"