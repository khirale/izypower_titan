from __future__ import annotations

from datetime import datetime
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
STORAGE_KEY_PREFIX = "izypower_titan_calibration"


class TitanCalibrationStorage:
    def __init__(self, hass: HomeAssistant, entry_id: str, host: str) -> None:
        safe_host = host.replace(".", "_")
        self._store = Store(
            hass,
            STORAGE_VERSION,
            f"{STORAGE_KEY_PREFIX}_{entry_id}_{safe_host}",
        )
        self._data: dict = {}

    async def async_load(self) -> None:
        data = await self._store.async_load()
        self._data = data or {}
        _LOGGER.debug("Calibration storage chargé : %s", self._data)

    async def async_save_last_full_charge(self, dt: datetime) -> None:
        self._data["last_full_charge"] = dt.isoformat()
        await self._store.async_save(self._data)
        _LOGGER.info("✅ Dernière charge complète enregistrée : %s", dt.isoformat())

    def get_last_full_charge(self) -> datetime | None:
        ts = self._data.get("last_full_charge")
        if ts is None:
            return None
        try:
            return datetime.fromisoformat(ts)
        except (ValueError, TypeError):
            _LOGGER.warning("Timestamp de calibration invalide en storage : %s", ts)
            return None
