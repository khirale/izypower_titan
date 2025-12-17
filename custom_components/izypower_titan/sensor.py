from homeassistant.components.sensor import (
    SensorEntity, 
    SensorDeviceClass, 
    SensorEntityDescription, 
    SensorStateClass
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.core import callback
from homeassistant.util import dt as dt_util
from dataclasses import dataclass, field
from typing import Final, Any
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfPower,
    PERCENTAGE
)
import logging
from .const import DOMAIN, ID_META
from .utils import normalize_unit, map_device_class, map_state_class

_LOGGER = logging.getLogger(__name__)

@dataclass(frozen=True, kw_only=True)
class IzypowerSensorEntityDescription(SensorEntityDescription):
    """Custom entity description class for Izypower sensors."""
    name: str = ""
    coefficient: float = 1.0
    state_mapping: dict[int, str] = field(default_factory=dict)
    translation_key: str | None = None
    entity_category: EntityCategory | None = None

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for key, meta in ID_META.items():
        state_mapping = meta.get("state_mapping", {})
        native_unit = normalize_unit(meta.get("unit"))
        device_class = map_device_class(meta.get("dev_class"))
        state_class = map_state_class(meta.get("state_class"))
        entities.append(
            IzypowerSensorEntity(
                coordinator=coordinator,
                description=IzypowerSensorEntityDescription(
                    key=str(key),
                    name=meta.get("name", f"TITAN - {key}"),
                    native_unit_of_measurement=native_unit,
                    device_class=device_class,
                    state_class=state_class,
                    coefficient=meta.get("coefficient", 1.0),
                    state_mapping=state_mapping,
                )
            )
        )

    entities.append(
        IzypowerConnectivitySensor(
            coordinator,
            "connectivity_status",
            "TITAN - Connectivity"
        )
    )

    entities.append(
        IzypowerConnectivityUptimeSensor(
            coordinator,
            "connectivity_uptime",
            "TITAN - Connectivity Uptime"
        )
    )

    async_add_entities(entities)
    _LOGGER.info("Création de %d entités Izypower Titan", len(entities))

class IzypowerSensorEntity(CoordinatorEntity, SensorEntity, RestoreEntity):

    _attr_has_entity_name = True

    def __init__(self, coordinator, description: IzypowerSensorEntityDescription):
        super().__init__(coordinator)
        self.entity_description = description
        self._last_valid_value = None  # pour gestion TOTAL_INCREASING

        host = coordinator.config_entry.data.get("host", "unknown")
        sn = coordinator.config_entry.data.get("sn", "unknown")

        self._attr_unique_id = f"{DOMAIN}_{host}_{description.key}"

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            manufacturer="Izypower",
            name=f"Izypower Titan ({host})",
            model="Titan",
            serial_number=sn,
        )

        if description.device_class == SensorDeviceClass.ENUM:
            self._attr_options = list(set(description.state_mapping.values()))

    async def async_added_to_hass(self):
        await super().async_added_to_hass()

        if self.entity_description.state_class == SensorStateClass.TOTAL_INCREASING:
            last_state = await self.async_get_last_state()
            if last_state and last_state.state not in (None, "unknown", "unavailable"):
                try:
                    self._last_valid_value = float(last_state.state)
                    #_LOGGER.debug("Restored last value for %s: %s", self.entity_id, self._last_valid_value)
                except (ValueError, TypeError):
                    _LOGGER.debug("Could not restore last state for %s", self.entity_id)

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        raw_value = data.get(self.entity_description.key)
        #_LOGGER.debug("%s | key=%s | raw_value=%s | coordinator_keys=%s", self.entity_id, self.entity_description.key, raw_value, list(data.keys()))

        if raw_value is None:
            try:
                raw_value = data.get(int(self.entity_description.key))
            except Exception:
                pass

        #_LOGGER.debug("%s → raw_value: %s (type: %s)", self.entity_id, raw_value, type(raw_value))

        if self.entity_description.device_class == SensorDeviceClass.ENUM:
            if raw_value is None:
                return None

            try:
                if isinstance(raw_value, float) and raw_value.is_integer():
                    raw_value = int(raw_value)
                elif isinstance(raw_value, str) and raw_value.replace(".", "", 1).isdigit():
                    raw_value = int(float(raw_value))
                else:
                    raw_value = int(raw_value)
            except Exception as e:
                _LOGGER.debug("ENUM: valeur non castable (%s) → %s", raw_value, e)

            mapped_value = self.entity_description.state_mapping.get(raw_value)
            if mapped_value is not None:
                return mapped_value

            return str(raw_value)

        if raw_value is None:
            if self.entity_description.state_class == SensorStateClass.TOTAL_INCREASING:
                #_LOGGER.debug("%s → valeur None, retour du dernier état valide: %s", self.entity_id, self._last_valid_value)
                return self._last_valid_value
            return None

        try:
            new_value = float(raw_value) * self.entity_description.coefficient
        except Exception:
            new_value = raw_value

        # --------------------------------------------------
        # Gestion spécifique des temps charge/décharge
        # 11019 / 11020 : 9999 => 0 + suppression .0
        # --------------------------------------------------
        if self.entity_description.key in ("11019", "11020"):
            try:
                if float(new_value) == 9999:
                    return 0
                return int(float(new_value))
            except (TypeError, ValueError):
                return None

        if self.entity_description.state_class == SensorStateClass.TOTAL_INCREASING:
            self._last_valid_value = new_value
            return new_value

        return new_value

class IzypowerOptionSensor(SensorEntity):

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, entry, coordinator, option_key: str, name: str, unit: str):
        self.entry = entry
        self.coordinator = coordinator
        self.option_key = option_key
        host = entry.data.get("host", "unknown")
        self._attr_unique_id = (
            f"{DOMAIN}_{host}_titan_{option_key}"
        )

        self._attr_name = f"TITAN - {name}"

        self._attr_native_unit_of_measurement = unit

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer="Izypower",
            name=f"Izypower Titan ({host})",
            model="Titan",
            serial_number=entry.data.get("sn", "unknown"),
        )

    @property
    def native_value(self):
        return self.entry.options.get(self.option_key)

class IzypowerConnectivitySensor(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, key, name):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{coordinator.config_entry.data.get('host')}_connectivity"
        self._attr_name = name

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            manufacturer="Izypower",
            name=f"Izypower Titan ({coordinator.config_entry.data.get('host', 'unknown')})",
            model="Titan",
            serial_number=coordinator.config_entry.data.get("sn", "unknown"),
        )

    @property
    def native_value(self):
        if getattr(self.coordinator, "last_http_ok", False):
            return "OK"
        return "KO"

class IzypowerConnectivityUptimeSensor(CoordinatorEntity, SensorEntity, RestoreEntity):
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = PERCENTAGE

    def __init__(self, coordinator, key, name):
        super().__init__(coordinator)
        host = coordinator.config_entry.data.get("host", "unknown")

        self._attr_unique_id = f"{DOMAIN}_{host}_connectivity_uptime"
        self._attr_name = name

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
            manufacturer="Izypower",
            name=f"Izypower Titan ({host})",
            model="Titan",
            serial_number=coordinator.config_entry.data.get("sn", "unknown"),
        )

        self._ok = 0
        self._total = 0
        self._day = None  # string "YYYY-MM-DD"

    async def async_added_to_hass(self):
        """Restaure les compteurs après reboot."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if not last_state:
            return

        attrs = last_state.attributes or {}

        try:
            self._ok = int(attrs.get("ok", 0))
        except (TypeError, ValueError):
            self._ok = 0

        try:
            self._total = int(attrs.get("total", 0))
        except (TypeError, ValueError):
            self._total = 0

        day = attrs.get("day")
        if isinstance(day, str):
            self._day = day

    @callback
    def _handle_coordinator_update(self) -> None:
        """Appelé à chaque update du coordinator."""
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

