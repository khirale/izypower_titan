from __future__ import annotations

import logging

from homeassistant.components.button import ButtonEntity
from homeassistant.helpers import entity_registry as er
from homeassistant.exceptions import HomeAssistantError
from .const import DOMAIN, CONF_CONNECTION_MODE, CONNECTION_MODE_LABELS, CONTROL, ENTITY_SCOPE_CLUSTER, ENTITY_SCOPE_UNIT

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinators = hass.data[DOMAIN][entry.entry_id]

    mode = entry.data.get(CONF_CONNECTION_MODE)
    mode_label = CONNECTION_MODE_LABELS.get(mode)

    cluster = entry.data.get("cluster", {})
    master_ip = cluster.get("master")

    entities = []

    for coordinator in coordinators.values():
        candidates = [
            IzypowerTitanRealtimeButton(coordinator),
            IzypowerTitanChargeButton(coordinator),
            IzypowerSelfConsumedModeButton(coordinator),
            IzypowerTitanDischargeButton(coordinator),
            IzypowerTitanStopButton(coordinator),
            IzypowerTitanCloudChargeButton(coordinator),
            IzypowerTitanCloudDischargeButton(coordinator),
            IzypowerTitanCloudAutoButton(coordinator),
            IzypowerTitanCloudStandbyModeButton(coordinator),
        ]

        for entity in candidates:
            if hasattr(entity, 'scope') and entity.scope == ENTITY_SCOPE_CLUSTER:
                if coordinator.host != master_ip:
                    continue
                    
            if CONTROL != "selected":
                entities.append(entity)
                continue

            if entity.profile == "common":
                entities.append(entity)
            elif entity.profile == mode_label:
                entities.append(entity)

    async_add_entities(entities)


class IzypowerTitanBaseButton(ButtonEntity):
    _attr_has_entity_name = True
    profile: str = "common"
    scope: str = ENTITY_SCOPE_CLUSTER
    
    def __init__(self, coordinator, unique_suffix: str, name: str):
        self.coordinator = coordinator
        entry = coordinator.config_entry
        host = coordinator.host

        self._host = host
        self._attr_unique_id = f"{DOMAIN}_{host}_{unique_suffix}"
        self._attr_name = name
        self._attr_device_info = coordinator.device_info


class IzypowerTitanRealtimeButton(IzypowerTitanBaseButton):
    profile = "MR1"
    scope = ENTITY_SCOPE_CLUSTER
    
    def __init__(self, coordinator):
        super().__init__(coordinator, "realtime", "Realtime mode")

    async def async_press(self) -> None:
        _LOGGER.info("Setting Titan to Realtime mode")
        await self.coordinator.api.async_set_realtime_mode()


class IzypowerTitanStopButton(IzypowerTitanBaseButton):
    profile = "MR1"
    scope = ENTITY_SCOPE_CLUSTER
    
    def __init__(self, coordinator):
        super().__init__(coordinator, "stop", "Standby")

    async def async_press(self) -> None:
        _LOGGER.info("Setting Titan to Stop mode")
        await self.coordinator.api.async_stop()


class IzypowerSelfConsumedModeButton(IzypowerTitanBaseButton):
    profile = "MR1"
    scope = ENTITY_SCOPE_CLUSTER
    
    def __init__(self, coordinator):
        super().__init__(coordinator, "self-consumed mode", "Self-Consumed mode")

    async def async_press(self) -> None:
        _LOGGER.info("Setting Titan to Self-consumed mode")
        await self.coordinator.api.async_set_selfconsumed_mode()


class IzypowerTitanChargeButton(IzypowerTitanBaseButton):
    profile = "MR1"
    scope = ENTITY_SCOPE_CLUSTER
    
    def __init__(self, coordinator):
        super().__init__(coordinator, "charge", "Start Charge")

    def _get_number_entity_id(self, suffix: str) -> str | None:
        ent_reg = er.async_get(self.hass)

        unique_id = f"{DOMAIN}_{self._host}_{suffix}"
        entry = ent_reg.async_get_entity_id("number", DOMAIN, unique_id)
        return entry

    async def async_press(self) -> None:
        power_eid = self._get_number_entity_id("charge_discharge_power")
        soc_eid = self._get_number_entity_id("charge_soc_limit")

        if not power_eid or not soc_eid:
            raise HomeAssistantError("Paramètres de charge manquants.")

        power_state = self.hass.states.get(power_eid)
        soc_state = self.hass.states.get(soc_eid)

        if not power_state or not soc_state:
            raise HomeAssistantError("Impossible de lire les paramètres de charge (state absent).")

        try:
            power = int(float(power_state.state))
            soc = int(float(soc_state.state))
        except (TypeError, ValueError) as err:
            raise HomeAssistantError(f"Valeurs invalides: power={power_state.state}, soc={soc_state.state}") from err

        _LOGGER.info("Start Charge: power=%sW soc_limit=%s%%", power, soc)
        await self.coordinator.api.async_charge(power=power, soc_limit=soc,max_power=self.coordinator.max_charge_power)


class IzypowerTitanDischargeButton(IzypowerTitanBaseButton):
    profile = "MR1"
    scope = ENTITY_SCOPE_CLUSTER
    
    def __init__(self, coordinator):
        super().__init__(coordinator, "discharge", "Start Discharge")

    def _get_number_entity_id(self, suffix: str) -> str | None:
        ent_reg = er.async_get(self.hass)
        unique_id = f"{DOMAIN}_{self._host}_{suffix}"
        entry = ent_reg.async_get_entity_id("number", DOMAIN, unique_id)
        return entry

    async def async_press(self) -> None:
        ent_reg = er.async_get(self.hass)
        
        power_eid = self._get_number_entity_id("charge_discharge_power")
        soc_eid = None
        for entity_entry in er.async_entries_for_config_entry(ent_reg, self.coordinator.config_entry.entry_id):
            if entity_entry.unique_id.endswith("_6105"):
                soc_eid = entity_entry.entity_id
                break

        if not power_eid or not soc_eid:
            raise HomeAssistantError(
                f"Entités introuvables (Power: {power_eid}, SOC: {soc_eid}). "
                "Vérifiez que le sensor 6105 est bien activé."
            )

        power_state = self.hass.states.get(power_eid)
        soc_state = self.hass.states.get(soc_eid)

        if not power_state or not soc_state:
            raise HomeAssistantError("Impossible de lire les états des entités.")

        if soc_state.state in ("unavailable", "unknown"):
            raise HomeAssistantError("Le SoC de la batterie n'est pas disponible pour le moment.")

        try:
            power = int(float(power_state.state))
            current_soc = int(float(soc_state.state))
        except (TypeError, ValueError) as err:
            raise HomeAssistantError(f"Valeurs invalides : {err}")

        _LOGGER.info(
            "Start Discharge : host=%s, power=%sW, soc_actuel=%s%%", 
            self._host, power, current_soc
        )

        await self.coordinator.api.async_discharge(power=power, soc_limit=current_soc,  max_power=self.coordinator.max_discharge_power)


class IzypowerTitanCloudChargeButton(IzypowerTitanBaseButton):
    profile = "Smart IA"
    scope = ENTITY_SCOPE_CLUSTER
    
    def __init__(self, coordinator):
        super().__init__(coordinator, "cloud_charge", "Start Charge")

    def _get_number_entity_id(self, suffix: str) -> str | None:
        ent_reg = er.async_get(self.hass)
        unique_id = f"{DOMAIN}_{self._host}_{suffix}"
        return ent_reg.async_get_entity_id("number", DOMAIN, unique_id)

    async def async_press(self) -> None:
        device_sn = self.coordinator.serial_number
        
        power_eid = self._get_number_entity_id("charge_discharge_power")
        if not power_eid:
            raise HomeAssistantError("Entité 'charge_discharge_power' introuvable.")

        state = self.hass.states.get(power_eid)
        if not state or state.state in ("unknown", "unavailable"):
            raise HomeAssistantError("La valeur de puissance SmartIA est indisponible.")

        try:
            power = int(float(state.state))
        except (TypeError, ValueError):
            raise HomeAssistantError(f"Valeur de puissance invalide : {state.state}")

        if not device_sn:
            raise HomeAssistantError("Serial Number (ID 0) manquant dans le coordinateur.")

        _LOGGER.info("SmartIA Charge Press: SN=%s, Power=%sW", device_sn, power)
        
        await self.coordinator.cloud_api.async_cloud_manual_charge(
            device_id=device_sn, 
            power_watts=power
        )


class IzypowerTitanCloudDischargeButton(IzypowerTitanBaseButton):
    profile = "Smart IA"
    scope = ENTITY_SCOPE_CLUSTER

    def __init__(self, coordinator):
        super().__init__(coordinator, "cloud_discharge", "Start Discharge")

    def _get_number_entity_id(self, suffix: str) -> str | None:
        ent_reg = er.async_get(self.hass)
        unique_id = f"{DOMAIN}_{self._host}_{suffix}"
        return ent_reg.async_get_entity_id("number", DOMAIN, unique_id)

    async def async_press(self) -> None:
        device_sn = self.coordinator.serial_number

        power_eid = self._get_number_entity_id("charge_discharge_power")
        if not power_eid:
            raise HomeAssistantError("Entité 'charge_discharge_power' introuvable.")

        state = self.hass.states.get(power_eid)
        if not state or state.state in ("unknown", "unavailable"):
            raise HomeAssistantError("La valeur de puissance SmartIA est indisponible.")

        try:
            power = int(float(state.state))
        except (TypeError, ValueError):
            raise HomeAssistantError(f"Valeur de puissance invalide : {state.state}")

        if not device_sn:
            raise HomeAssistantError("Serial Number (ID 0) manquant dans le coordinateur.")

        _LOGGER.info("SmartIA Discharge Press: SN=%s, Power=%sW", device_sn, power)

        await self.coordinator.cloud_api.async_cloud_manual_discharge(
            device_id=device_sn,
            power_watts=power
        )


class IzypowerTitanCloudAutoButton(IzypowerTitanBaseButton):
    profile = "Smart IA"
    scope = ENTITY_SCOPE_CLUSTER
    
    def __init__(self, coordinator):
        super().__init__(coordinator, "cloud_auto", "Intelligent Mode")

    async def async_press(self) -> None:
        device_sn = self.coordinator.serial_number
        if not device_sn:
            raise HomeAssistantError("Serial Number (ID 0) manquant.")

        _LOGGER.info("Cloud Intelligent Mode Press: SN=%s", device_sn)
        await self.coordinator.cloud_api.async_intelligent_mode(device_id=device_sn)


class IzypowerTitanCloudStandbyModeButton(IzypowerTitanBaseButton):
    profile = "Smart IA"
    scope = ENTITY_SCOPE_CLUSTER
    
    def __init__(self, coordinator):
        super().__init__(coordinator, "standby mode", "Standby mode")

    async def async_press(self) -> None:
        device_sn = self.coordinator.serial_number
        if not device_sn:
            raise HomeAssistantError("Serial Number (ID 0) manquant.")

        _LOGGER.info("Setting Titan to SmartIA Standby mode SN=%s", device_sn)
        await self.coordinator.cloud_api.async_cloud_manual_standby(device_id=device_sn)
