"""Diagnostics support for Izypower Titan."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

TO_REDACT = {"username", "password", "token", "wifi_ssid", "wifi_ip"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    coordinators = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})

    coordinators_diag: dict[str, Any] = {}

    for host, coord in coordinators.items():
        data = coord.data or {}

        coordinators_diag[host] = {
            "host": coord.host,
            "serial_number": coord.serial_number,
            "max_charge_power": coord.max_charge_power,
            "max_discharge_power": coord.max_discharge_power,
            "is_cluster": coord.is_cluster,
            "last_update_success": coord.last_update_success,
            "last_http_ok": coord.last_http_ok,
            "consecutive_errors": coord._consecutive_errors,
            "last_successful_poll": (
                coord._last_successful_poll.isoformat()
                if coord._last_successful_poll
                else None
            ),
            "last_links_discovery": (
                coord._links_last_discovery.isoformat()
                if coord._links_last_discovery
                else None
            ),
            "links_discovered": list(coord.links.keys()),
            "poll_ids_count": len(coord._poll_ids),
            "data_keys_count": len(data),
            "data": async_redact_data(data, TO_REDACT),
            "scan_interval_seconds": (
                coord.update_interval.total_seconds()
                if coord.update_interval
                else None
            ),
        }

    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": dict(entry.options),
            "version": entry.version,
            "title": entry.title,
        },
        "coordinators": coordinators_diag,
    }
