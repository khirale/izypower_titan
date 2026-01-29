from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.const import PERCENTAGE

from .const import DOMAIN, LINK_ID_META
import logging

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinators = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for coordinator in coordinators.values():
        for link in coordinator.links.values():
            sn = link["sn"]
            ids = link["ids"]

            for sensor_id in ids:
                meta = LINK_ID_META.get(sensor_id)
                if not meta:
                    continue

                entities.append(
                    IzypowerLinkSensor(
                        coordinator=coordinator,
                        link_sn=sn,
                        sensor_id=sensor_id,
                        meta=meta,
                    )
                )

    async_add_entities(entities)

class IzypowerLinkSensor(CoordinatorEntity, SensorEntity):

    _attr_has_entity_name = True

    def __init__(self, coordinator, link_sn: str, sensor_id: int, meta: dict):
        super().__init__(coordinator)

        self._link_sn = link_sn
        self._sensor_id = sensor_id


        self._meta = meta
        self.entity_description = SensorEntityDescription(
            key=meta.get("key"),
            name=meta.get("name"),
            native_unit_of_measurement=meta.get("unit"),
            device_class=meta.get("dev_class"),
            state_class=meta.get("state_class"),
        )

        host = coordinator.host

        self._attr_unique_id = (
            f"{DOMAIN}_{host}_link_{link_sn}_{sensor_id}"
        )

        self._attr_name = meta.get("name")

        self._attr_native_unit_of_measurement = meta.get("unit")
        self._attr_device_class = meta.get("dev_class")
        self._attr_state_class = meta.get("state_class")

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{host}_link_{link_sn}")},
            name=f"Izypower Titan ({host}) – Link ({link_sn})",
            manufacturer="Izypower",
            model="Titan Link",
            via_device=(DOMAIN, coordinator.serial_number),
        )

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        raw = data.get(str(self._sensor_id))

        if raw is None:
            return None

        if self._sensor_id in (9032, 9051, 9070, 9165, 9218):
            return str(raw)

        try:
            return float(raw)
        except Exception:
            return raw