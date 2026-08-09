from __future__ import annotations

from datetime import datetime, timedelta
import logging

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_FULL_CHARGE_CONFIRMATION_MINUTES,
    DEFAULT_FULL_CHARGE_CONFIRMATION_MINUTES,
)

_LOGGER = logging.getLogger(__name__)

EVENT_FULL_CHARGE_CONFIRMED = f"{DOMAIN}_full_charge_confirmed"

_SOC_KEY = "6002"
_STATE_KEY = "6001"

BATTERY_STATE_STATIC = 1000


async def async_setup_entry(
    hass: HomeAssistant, entry, async_add_entities
) -> None:
    coordinators = hass.data[DOMAIN][entry.entry_id]

    entities = []

    for host, coordinator in coordinators.items():
        if coordinator.calibration_storage is None:
            _LOGGER.warning(
                "calibration_storage non disponible sur %s, binary sensor ignoré", host
            )
            continue
        entities.append(
            TitanFullChargeConfirmedSensor(coordinator)
        )

    async_add_entities(entities)


class TitanFullChargeConfirmedSensor(CoordinatorEntity, BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_device_class = None
    _attr_icon = "mdi:battery-check"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator)

        self._attr_unique_id = f"{DOMAIN}_{coordinator.host}_full_charge_confirmed"
        self._attr_name = "Charge complète confirmée"
        self._attr_device_info = coordinator.device_info

        self._condition_met_since: datetime | None = None
        self._session_recorded: bool = False
        self._startup_session_checked: bool = False

    def _confirmation_delay(self) -> timedelta:
        minutes = self.coordinator.config_entry.options.get(
            CONF_FULL_CHARGE_CONFIRMATION_MINUTES,
            DEFAULT_FULL_CHARGE_CONFIRMATION_MINUTES,
        )
        return timedelta(minutes=int(minutes))


    @callback
    def _handle_coordinator_update(self) -> None:
        data = self.coordinator.data or {}

        try:
            soc = int(float(data.get(_SOC_KEY, 0)))
        except (TypeError, ValueError):
            soc = 0

        try:
            battery_state = int(float(data.get(_STATE_KEY, -1)))
        except (TypeError, ValueError):
            battery_state = -1

        condition_ok = (
            soc >= 100
            and battery_state == BATTERY_STATE_STATIC
        )

        now = dt_util.utcnow()

        if not self._startup_session_checked:
            self._startup_session_checked = True
            if condition_ok:
                last = self.coordinator.calibration_storage.get_last_full_charge()
                if last is not None:
                    if last.tzinfo is None:
                        last = last.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
                    if dt_util.now() - last < timedelta(hours=24):
                        self._session_recorded = True
                        _LOGGER.debug(
                            "Titan %s – 100%% déjà vrai au démarrage, session du %s "
                            "considérée déjà enregistrée",
                            self.coordinator.host, last.isoformat(),
                        )

        if condition_ok:
            if self._condition_met_since is None:
                self._condition_met_since = now
                _LOGGER.debug(
                    "Titan %s – Condition 100%% détectée (SOC=%s, State=Static), début délai %s",
                    self.coordinator.host, soc, self._confirmation_delay(),
                )

            elapsed = now - self._condition_met_since

            if elapsed >= self._confirmation_delay():
                self._attr_is_on = True
                if not self._session_recorded:
                    self._session_recorded = True
                    self.hass.async_create_task(
                        self._record_full_charge(now)
                    )
            else:
                self._attr_is_on = False
        else:
            if self._condition_met_since is not None:
                _LOGGER.debug(
                    "Titan %s – Condition 100%% perdue (SOC=%s, State=%s), reset timer",
                    self.coordinator.host, soc, battery_state,
                )
            self._condition_met_since = None
            self._session_recorded = False
            self._attr_is_on = False

        self.async_write_ha_state()

    async def _record_full_charge(self, confirmed_at_utc: datetime) -> None:
        local_dt = dt_util.as_local(confirmed_at_utc)
        storage = self.coordinator.calibration_storage

        if storage is None:
            _LOGGER.error("calibration_storage introuvable, enregistrement impossible")
            return

        await storage.async_save_last_full_charge(local_dt)

        self.hass.bus.async_fire(
            EVENT_FULL_CHARGE_CONFIRMED,
            {
                "entry_id": self.coordinator.config_entry.entry_id,
                "host": self.coordinator.host,
                "serial_number": self.coordinator.serial_number,
                "timestamp": local_dt.isoformat(),
            },
        )
        _LOGGER.info(
            "✅ Charge complète confirmée – Titan %s à %s",
            self.coordinator.host,
            local_dt.isoformat(),
        )


    @property
    def extra_state_attributes(self) -> dict:
        delay_s = self._confirmation_delay().total_seconds()

        if self._condition_met_since is None:
            elapsed_s = 0
        else:
            elapsed_s = min(
                (dt_util.utcnow() - self._condition_met_since).total_seconds(),
                delay_s,
            )

        return {
            "confirmation_delay_min": int(delay_s // 60),
            "confirmation_progress_pct": round((elapsed_s / delay_s) * 100) if delay_s else 0,
            "confirmation_progress_s": int(elapsed_s),
        }
