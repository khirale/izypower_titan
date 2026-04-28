from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorEntityDescription,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity import EntityCategory
from dataclasses import dataclass, field
from typing import Any
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfPower,
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
                            if meta.get("key") in ("alarm_code", "backup", "leds", "battery_cycle",)
                            else None
                        ),
                    ),
                )
            )

        mode = entry.data.get(CONF_CONNECTION_MODE)

        entities.extend(
            [
                IzypowerWifiRssiSensor(coordinator, "wifi_rssi", "TITAN - WiFi RSSI"),
                IzypowerMqttStatusSensor(coordinator, "mqtt_status", "TITAN - MQTT Server"),
                IzypowerWifiSsidSensor(coordinator, "wifi_ssid", "TITAN - WiFi SSID"),
                IzypowerWifiIpSensor(coordinator, "wifi_ip", "TITAN - WiFi IP"),
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

        if self.entity_description.key == "0":
            return str(raw_value)

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


class IzypowerWifiRssiSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = "dBm"
    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_state_class = "measurement"

    def __init__(self, coordinator, key, name):
        super().__init__(coordinator)
        host = coordinator.host

        self._attr_unique_id = f"{DOMAIN}_{host}_wifi_rssi"
        self._attr_name = name
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data or {}
        return data.get("wifi_rssi_dbm")


class IzypowerMqttStatusSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, key, name):
        super().__init__(coordinator)
        host = coordinator.host

        self._attr_unique_id = f"{DOMAIN}_{host}_mqtt_status"
        self._attr_name = name
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data or {}
        return data.get("mqtt_connected")

    @property
    def icon(self) -> str:
        return "mdi:server-network" if self.native_value == "Connected" else "mdi:server-network-off"


class IzypowerWifiSsidSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, key, name):
        super().__init__(coordinator)
        host = coordinator.host

        self._attr_unique_id = f"{DOMAIN}_{host}_wifi_ssid"
        self._attr_name = name
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data or {}
        return data.get("wifi_ssid")

    @property
    def icon(self) -> str:
        return "mdi:wifi"


class IzypowerWifiIpSensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, key, name):
        super().__init__(coordinator)
        host = coordinator.host

        self._attr_unique_id = f"{DOMAIN}_{host}_wifi_ip"
        self._attr_name = name
        self._attr_device_info = coordinator.device_info

    @property
    def native_value(self) -> str | None:
        data = self.coordinator.data or {}
        return data.get("wifi_ip")

    @property
    def icon(self) -> str:
        return "mdi:ip-network"