from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN, LINK_ID_META
from .utils import normalize_unit, map_device_class, map_state_class
import logging

_LOGGER = logging.getLogger(__name__)


def _build_link_entities(coordinator, sn: str, ids: list) -> list:
    entities = []
    for sensor_id in ids:
        meta = LINK_ID_META.get(sensor_id)
        if not meta:
            continue
        entities.append(IzypowerLinkSensor(coordinator, sn, sensor_id, meta))
    return entities


async def async_setup_entry(hass, entry, async_add_entities):
    coordinators = hass.data[DOMAIN][entry.entry_id]
    entities = []

    for coordinator in coordinators.values():
        for link in coordinator.links.values():
            entities.extend(_build_link_entities(coordinator, link["sn"], link["ids"]))

        def _on_new_link(link_data, coord=coordinator):
            new_entities = _build_link_entities(coord, link_data["sn"], link_data["ids"])
            if new_entities:
                _LOGGER.info(
                    "Ajout dynamique de %d entités pour la batterie Link SN=%s",
                    len(new_entities), link_data["sn"],
                )
                async_add_entities(new_entities)

        entry.async_on_unload(
            async_dispatcher_connect(
                hass,
                f"{DOMAIN}_new_link_{coordinator.host}",
                _on_new_link,
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
            native_unit_of_measurement=normalize_unit(meta.get("unit")),
            device_class=map_device_class(meta.get("dev_class")),
            state_class=map_state_class(meta.get("state_class")),
        )

        host = coordinator.host

        self._attr_unique_id = (
            f"{DOMAIN}_{host}_link_{link_sn}_{sensor_id}"
        )

        self._attr_name = meta.get("name")

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{host}_link_{link_sn}")},
            name=f"Izypower Titan ({host}) – Link ({link_sn})",
            manufacturer="Izypower",
            model="Titan Link",
            via_device=(DOMAIN, coordinator.device_identifier),
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