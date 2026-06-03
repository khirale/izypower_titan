from __future__ import annotations

import logging
from typing import Any, Dict
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    DOMAIN,
    DEFAULT_SCAN_INTERVAL,
    TITAN_IDS,
    LINK_ID_GROUPS,
    ID_META,
    LINK_ID_META,
)
from .izypower_api import IzypowerAPI
from .cloud_api import IzyCloudAPI

_LOGGER = logging.getLogger(__name__)

WIFI_CLOUD_INTERVAL = timedelta(seconds=60)
WATCHDOG_TIMEOUT = timedelta(minutes=5)


def _decimal_precision(val: float) -> int:
    s = f"{val:.10f}".rstrip("0")
    if "." not in s:
        return 0
    return len(s.split(".")[1])


class IzypowerTitanCoordinator(DataUpdateCoordinator[Dict[str, Any]]):

    def __init__(self, hass, entry: ConfigEntry, host: str, max_charge: int, max_discharge: int):
        scan_interval = entry.options.get(
            "scan_interval",
            entry.data.get("scan_interval", DEFAULT_SCAN_INTERVAL),
        )

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{host}",
            update_interval=timedelta(seconds=scan_interval),
        )

        self.host = host
        self.config_entry = entry
        self.session = async_get_clientsession(hass)

        self.api = IzypowerAPI(
            host=host,
            port=entry.data["port"],
            session=self.session,
        )

        self.cloud_api = IzyCloudAPI(
            username=entry.data.get("username", ""),
            password=entry.data.get("password", ""),
            session=self.session,
        )

        self.max_charge_power = int(max_charge)
        self.max_discharge_power = int(max_discharge)

        self.links: dict[str, dict[str, Any]] = {}
        self._links_last_discovery: datetime | None = None
        self._poll_ids: list[int] = list(TITAN_IDS)

        self._consecutive_errors = 0
        self._max_consecutive_errors = 3
        self._first_update = True
        self.serial_number: str | None = None
        self.last_http_ok = False

        self._last_successful_poll: datetime | None = None
        self._last_wifi_cloud_poll: datetime | None = None
        self._cached_wifi_cloud_data: dict[str, Any] = {}

        self._category_a_ids: set[str] = set()
        self._category_d_ids: set[str] = set()
        self._category_b_ids: set[str] = set()
        self._category_c_ids: set[str] = set()
        self._build_categories()

        self._last_valid_energy: dict[str, float] = {}
        self._last_energy_ts: dict[str, datetime] = {}
        self._last_valid_b: dict[str, float] = {}
        self._last_valid_c: dict[str, Any] = {}

        self.calibration_storage = None

    def _is_daily_energy(self, meta: dict[str, Any]) -> bool:
        key = meta.get("key", "").lower()
        return any(token in key for token in ("daily", "today", "day"))

    def _build_categories(self) -> None:
        all_meta: dict[Any, dict[str, Any]] = {}
        all_meta.update(ID_META)
        all_meta.update(LINK_ID_META)

        for raw_id, meta in all_meta.items():
            sid = str(raw_id)
            dev_class = meta.get("dev_class")
            state_class = meta.get("state_class")

            if dev_class == "energy" and state_class in ("total", "total_increasing"):
                if self._is_daily_energy(meta):
                    self._category_d_ids.add(sid)
                else:
                    self._category_a_ids.add(sid)

            elif state_class == "measurement" and dev_class in {
                "power",
                "battery",
                "temperature",
                "voltage",
                "current",
            }:
                self._category_b_ids.add(sid)

            else:
                self._category_c_ids.add(sid)

        _LOGGER.debug(
            "Coordinator categories | A=%s | D=%s | B=%s | C=%s",
            sorted(self._category_a_ids),
            sorted(self._category_d_ids),
            sorted(self._category_b_ids),
            sorted(self._category_c_ids),
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        now = datetime.now()
        self.last_http_ok = False

        try:
            if (self._links_last_discovery is None or
                    now - self._links_last_discovery >= timedelta(hours=1)):
                await self._discover_links()
                self._links_last_discovery = now

            new_data: Dict[str, Any] = await self.api.fetch_data(self._poll_ids)

            if not new_data:
                if self.data:
                    return self.data
                raise UpdateFailed("No data received from Titan device")

            raw_data: dict[str, Any] = {str(k): v for k, v in new_data.items()}

            sn_value = raw_data.get("0")
            if sn_value is not None:
                try:
                    self.serial_number = str(int(float(sn_value)))
                except Exception:
                    self.serial_number = str(sn_value)

            self._consecutive_errors = 0
            self.last_http_ok = True

            validated_data: dict[str, Any] = {}

            for sid in self._category_d_ids:
                raw_value = raw_data.get(sid)
                if raw_value is None:
                    _LOGGER.debug("D %s missing", sid)
                    continue
                try:
                    validated_data[sid] = float(raw_value)
                except (TypeError, ValueError):
                    _LOGGER.debug("D %s rejected (non numeric): %s", sid, raw_value)
                    continue

            for sid in self._category_a_ids:
                raw_value = raw_data.get(sid)

                if raw_value is None:
                    if sid in self._last_valid_energy:
                        validated_data[sid] = self._last_valid_energy[sid]
                        _LOGGER.debug("A %s missing, keep last=%s", sid, validated_data[sid])
                    continue

                try:
                    value = float(raw_value)
                except (TypeError, ValueError):
                    if sid in self._last_valid_energy:
                        validated_data[sid] = self._last_valid_energy[sid]
                    _LOGGER.debug("A %s rejected (non numeric): %s", sid, raw_value)
                    continue
                
                if self._first_update:
                    self._last_valid_energy[sid] = value
                    self._last_energy_ts[sid] = now
                    validated_data[sid] = value
                    continue
                
                
                if sid not in self._last_valid_energy:
                    self._last_valid_energy[sid] = value
                    self._last_energy_ts[sid] = now
                    validated_data[sid] = value
                    continue

                last_value = self._last_valid_energy[sid]
                last_ts = self._last_energy_ts.get(sid, now)

                if value < last_value:
                    validated_data[sid] = last_value
                    _LOGGER.debug(
                        "A %s rejected (regression): %s < %s",
                        sid,
                        value,
                        last_value,
                    )
                    continue

                dt_h = max((now - last_ts).total_seconds(), 1) / 3600.0

                # After a long offline period, accept the new value as baseline
                # without delta check — the device was simply unreachable
                if dt_h > 1.0:
                    self._last_valid_energy[sid] = value
                    self._last_energy_ts[sid] = now
                    validated_data[sid] = value
                    _LOGGER.debug(
                        "A %s baseline reset after %.1fh absence: %s",
                        sid, dt_h, value,
                    )
                    continue

                p_max_w = max(self.max_charge_power, self.max_discharge_power)
                energy_max_wh = p_max_w * dt_h * 2.5

                meta = ID_META.get(int(sid)) or LINK_ID_META.get(int(sid)) or {}
                unit = meta.get("unit")

                delta_e_max = energy_max_wh if unit == "Wh" else energy_max_wh / 1000.0
                delta_e = value - last_value
                precision = _decimal_precision(value)

                if round(delta_e, precision) > round(delta_e_max, precision):
                    validated_data[sid] = last_value
                    _LOGGER.debug(
                        "A %s rejected (ΔE too high): raw=%s last=%s ΔE=%s max=%s",
                        sid,
                        raw_value,
                        last_value,
                        delta_e,
                        delta_e_max,
                    )
                    continue

                self._last_valid_energy[sid] = value
                self._last_energy_ts[sid] = now
                validated_data[sid] = value

            validated_b_data: dict[str, float] = {}
            p_max_allowed = max(self.max_charge_power, self.max_discharge_power) * 2.5

            for sid in self._category_b_ids:
                raw_value = raw_data.get(sid)

                if raw_value is None:
                    if sid in self._last_valid_b:
                        validated_b_data[sid] = self._last_valid_b[sid]
                        _LOGGER.debug("B %s missing, keep last=%s", sid, validated_b_data[sid])
                    continue

                try:
                    value = float(raw_value)
                except (TypeError, ValueError):
                    if sid in self._last_valid_b:
                        validated_b_data[sid] = self._last_valid_b[sid]
                    _LOGGER.debug("B %s rejected (non numeric): %s", sid, raw_value)
                    continue

                meta = ID_META.get(int(sid)) or LINK_ID_META.get(int(sid)) or {}
                dev_class = meta.get("dev_class")

                if dev_class == "battery" and not (0 <= value <= 110):
                    if sid in self._last_valid_b:
                        validated_b_data[sid] = self._last_valid_b[sid]
                    _LOGGER.debug("B %s rejected (SOC out of range): %s", sid, value)
                    continue

                if dev_class == "power" and abs(value) > p_max_allowed:
                    if sid in self._last_valid_b:
                        validated_b_data[sid] = self._last_valid_b[sid]
                    _LOGGER.debug("B %s rejected (power out of range): %s", sid, value)
                    continue

                if dev_class == "temperature" and not (-30 <= value <= 90):
                    if sid in self._last_valid_b:
                        validated_b_data[sid] = self._last_valid_b[sid]
                    _LOGGER.debug("B %s rejected (temperature out of range): %s", sid, value)
                    continue

                self._last_valid_b[sid] = value
                validated_b_data[sid] = value

            validated_c_data: dict[str, Any] = {}
            for sid in self._category_c_ids:
                if sid not in raw_data:
                    if sid in self._last_valid_c:
                        validated_c_data[sid] = self._last_valid_c[sid]
                        _LOGGER.debug("C %s missing, keep last=%s", sid, validated_c_data[sid])
                    continue

                raw_value = raw_data.get(sid)

                if raw_value is None:
                    if sid in self._last_valid_c:
                        validated_c_data[sid] = self._last_valid_c[sid]
                        _LOGGER.debug("C %s is None, keep last=%s", sid, validated_c_data[sid])
                    continue

                try:
                    value = int(raw_value)
                except (TypeError, ValueError):
                    value = str(raw_value)
                    _LOGGER.debug("C %s casted to string: %s", sid, raw_value)

                self._last_valid_c[sid] = value
                validated_c_data[sid] = value

            merged = self.data.copy() if self.data else {}
            merged.update(validated_data)
            merged.update(validated_b_data)
            merged.update(validated_c_data)

            for sid, val in raw_data.items():
                if sid not in merged:
                    merged[sid] = val

            if (self._last_wifi_cloud_poll is None
                    or now - self._last_wifi_cloud_poll >= WIFI_CLOUD_INTERVAL):
                try:
                    wifi_data = await self.api.async_get_wifi_config()
                    sta = wifi_data.get("sta", {})
                    rssi_raw = sta.get("rssi")
                    if rssi_raw is not None:
                        self._cached_wifi_cloud_data["wifi_rssi_dbm"] = (float(rssi_raw) / 2) - 100
                    if sta.get("ssid") is not None:
                        self._cached_wifi_cloud_data["wifi_ssid"] = str(sta.get("ssid"))
                    if sta.get("ip") is not None:
                        self._cached_wifi_cloud_data["wifi_ip"] = str(sta.get("ip"))
                except Exception as err:
                    _LOGGER.debug("WiFi.GetConfig failed: %s", err)

                try:
                    cloud_list = await self.api.async_get_cloud_status()
                    for item in cloud_list:
                        if item.get("cloud") == ":IGEN_MQTT":
                            self._cached_wifi_cloud_data["mqtt_connected"] = (
                                "Connected" if item.get("connected") else "Disconnected"
                            )
                            break
                except Exception as err:
                    _LOGGER.debug("Cloud.GetStatus failed: %s", err)

                self._last_wifi_cloud_poll = now

            merged.update(self._cached_wifi_cloud_data)

            self._first_update = False
            self._last_successful_poll = now
            return merged

        except Exception as err:
            self.last_http_ok = False
            self._consecutive_errors += 1

            if (self._last_successful_poll is not None
                    and now - self._last_successful_poll > WATCHDOG_TIMEOUT):
                _LOGGER.warning(
                    "Watchdog: aucun poll réussi depuis %s, marquage indisponible",
                    WATCHDOG_TIMEOUT,
                )
                raise UpdateFailed(
                    f"Watchdog timeout exceeded ({WATCHDOG_TIMEOUT})"
                )

            if self.data and self._consecutive_errors <= self._max_consecutive_errors:
                return self.data

            raise UpdateFailed(err)

    @property
    def is_cluster(self) -> bool:
        raw = (self.data or {}).get("606")
        try:
            raw = int(float(raw))
        except (TypeError, ValueError):
            return False
        return raw in (1000, 1001)

    async def async_cloud_set_charge_power(self, device_id: str, power: int):
        return await self.cloud_api.async_set_charge_power(
            device_id=device_id,
            max_in=power,
            is_cluster=self.is_cluster,
        )

    async def async_cloud_set_discharge_power(self, device_id: str, power: int):
        return await self.cloud_api.async_set_discharge_power(
            device_id=device_id,
            max_out=power,
            is_cluster=self.is_cluster,
        )

    async def async_set_soc_security_register(self, value: int):
        """Wrapper method to call API with SOC security register."""
        return await self.api.async_set_soc_security_register(value)

    async def async_set_max_power_register(self, value: int):
        """Wrapper method to call API with max_charge_power parameter."""
        return await self.api.async_set_max_power_register(value, self.max_charge_power)

    async def async_set_max_discharge_power_register(self, value: int):
        from .const import CONF_TITAN_COUNT, CONF_OVERRIDE_RESPONSIBILITY, DISCHARGE_PER_TITAN, MAX_ABS_PER_TITAN
        
        override = self.config_entry.data.get(CONF_OVERRIDE_RESPONSIBILITY, False)
        
        if override:
            max_power = MAX_ABS_PER_TITAN  # 2400W
        else:
            max_power = DISCHARGE_PER_TITAN  # 800W
        
        return await self.api.async_set_max_discharge_power_register(value, max_power)

    async def _discover_links(self) -> None:
        sn_ids = [group[0] for group in LINK_ID_GROUPS]

        try:
            data = await self.api.fetch_data(sn_ids)
        except Exception as err:
            _LOGGER.debug("Link discovery fetch failed: %s", err)
            return

        for group in LINK_ID_GROUPS:
            sn_id = group[0]
            sn = data.get(str(sn_id))
            if not sn:
                continue

            try:
                sn = str(int(float(sn)))
            except Exception:
                sn = str(sn)

            if sn in self.links:
                continue

            self.links[sn] = {"sn": sn, "ids": group}

            for sensor_id in group:
                if sensor_id not in self._poll_ids:
                    self._poll_ids.append(sensor_id)

            _LOGGER.info("Nouvelle batterie Link découverte : SN=%s", sn)
            async_dispatcher_send(
                self.hass,
                f"{DOMAIN}_new_link_{self.host}",
                {"sn": sn, "ids": group},
            )

    @property
    def device_info(self) -> DeviceInfo:
        identifiers = {(DOMAIN, self.serial_number or self.host)}

        return DeviceInfo(
            identifiers=identifiers,
            manufacturer="Izypower",
            name=f"Izypower Titan ({self.host})",
            model="Titan - Intégration personnalisée par Khirale",
            serial_number=self.serial_number,
        )

    async def async_shutdown(self) -> None:
        _LOGGER.debug("Shutting down Izypower coordinator")
