from __future__ import annotations
import logging
from typing import Any, Dict
from datetime import datetime, timedelta
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, DEFAULT_SCAN_INTERVAL, TITAN_IDS
from .izypower_api import IzypowerAPI

_LOGGER = logging.getLogger(__name__)



class IzypowerTitanCoordinator(DataUpdateCoordinator[Dict[str, Any]]):

    def __init__(self, hass, entry: ConfigEntry):
        scan_interval = entry.options.get(
            "scan_interval",
            entry.data.get("scan_interval", DEFAULT_SCAN_INTERVAL),
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=scan_interval),
        )

        self.config_entry = entry
        self.session = async_get_clientsession(hass)
        self.api = IzypowerAPI(
            host=entry.data["host"],
            port=entry.data["port"],
            session=self.session,
        )

        self._consecutive_errors = 0
        self._max_consecutive_errors = 3
        self._first_update = True

    @property
    def config(self) -> dict:
        return {**self.config_entry.data, **self.config_entry.options}

    async def _async_update_data(self) -> Dict[str, Any]:
        self.last_http_ok = False

        try:
            #_LOGGER.debug("Fetching %d Titan keys", len(TITAN_IDS))
            new_data: Dict[str, Any] = {}
            for key in TITAN_IDS:
                try:
                    #_LOGGER.debug("Titan API request → fetch_data([%s])", key)
                    result = await self.api.fetch_data([key])
                    #_LOGGER.debug("Titan API response → key=%s result=%s", key, result)
                    new_data.update(result)
                except Exception as e:
                    #_LOGGER.debug("Failed to fetch key %s: %s", key, e)
                    raise

            requested_keys = {str(k) for k in TITAN_IDS}
            received_keys = {str(k) for k in new_data.keys()}
            missing = requested_keys - received_keys
            #_LOGGER.debug("Titan API summary → requested=%d | received=%d | missing=%d | missing_keys=%s", len(requested_keys), len(received_keys), len(missing), sorted(list(missing)),)

            if not new_data:
                _LOGGER.warning("No new data received from Titan device")
                if self.data:
                    return self.data
                raise UpdateFailed("No data received from Titan device")

            sn_key = 0
            sn_value = new_data.get(sn_key) or new_data.get(str(sn_key))

            if sn_value is not None:
                try:
                    sn_value = int(float(sn_value))
                except:
                    sn_value = str(sn_value)

                self.hass.config_entries.async_update_entry(
                    self.config_entry,
                    data={
                        **self.config_entry.data,
                        "sn": str(sn_value)
                    }
                )
                _LOGGER.debug("Titan SN successfully stored: %s", sn_value)
            else:
                _LOGGER.debug("Titan SN key not found in new_data")

            if self._first_update:
                _LOGGER.info(
                    "First update successful — received %d/%d keys",
                    len(new_data),
                    len(TITAN_IDS),
                )
                self._first_update = False

            self._consecutive_errors = 0

            self.last_http_ok = True

            if self.data:
                merged = self.data.copy()
                merged.update(new_data)
                #_LOGGER.debug("Merged Titan dataset: %s", merged)
                return merged

            return new_data

        except Exception as err:
            self.last_http_ok = False
            self._consecutive_errors += 1

            if self._consecutive_errors <= self._max_consecutive_errors:
                _LOGGER.warning(
                    "Failed to update (attempt %d/%d): %s",
                    self._consecutive_errors,
                    self._max_consecutive_errors,
                    err,
                )
            else:
                _LOGGER.error("Persistent connection failure to device: %s", err)

            _LOGGER.error("Titan HTTP connectivity failed — all values forced to zero")

            zero_data = {str(k): 0 for k in TITAN_IDS}

            # Correction enum propre :
            zero_data["6001"] = -1
            zero_data["7101"] = -1
            zero_data["7120"] = -1
            zero_data["606"] = -1

            return zero_data

    async def async_shutdown(self) -> None:
        _LOGGER.debug("Shutting down Izypower coordinator")
