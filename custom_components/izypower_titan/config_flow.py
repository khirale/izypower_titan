import logging
from typing import Any
import voluptuous as vol
import json
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL, CONF_USERNAME, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectSelectorMode
from .cloud_api import IzyCloudAPI
from .izypower_api import IzypowerAPI

from .const import (
    DOMAIN, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, CONF_CONNECTION_MODE,
    CONF_TITAN_COUNT, CONF_OVERRIDE_RESPONSIBILITY, DEFAULT_MAX_CHARGE_POWER,
    DEFAULT_MAX_DISCHARGE_POWER, CHARGE_PER_TITAN, DISCHARGE_PER_TITAN,
    MAX_ABS_PER_TITAN, MODE_LOCAL, MODE_CLOUD, CONNECTION_MODE_LABELS,
    CLUSTER_ROLE, CLUSTER_MASTER, CLUSTER_SLAVE, CLUSTER_NO_CLUSTER,
    CONF_FULL_CHARGE_CONFIRMATION_MINUTES, DEFAULT_FULL_CHARGE_CONFIRMATION_MINUTES,
)

_LOGGER = logging.getLogger(__name__)

class IzypowerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 2

    def __init__(self):
        self._data = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return IzypowerOptionsFlowHandler(config_entry)

    @property
    def _is_reconfigure(self) -> bool:
        return self.source == config_entries.SOURCE_RECONFIGURE

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        entry = self._get_reconfigure_entry()
        self._data = dict(entry.data)
        return await self.async_step_user()

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors = {}

        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_hosts()

        default_mode = self._data.get(CONF_CONNECTION_MODE, MODE_LOCAL)
        default_count = str(self._data.get(CONF_TITAN_COUNT, "1"))
        default_port = self._data.get(CONF_PORT, DEFAULT_PORT)
        default_interval = self._data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

        schema = vol.Schema(
            {
                vol.Required(CONF_CONNECTION_MODE, default=default_mode): vol.In({MODE_LOCAL: "MR1", MODE_CLOUD: "Smart IA"}),
                vol.Required(CONF_TITAN_COUNT, default=default_count): SelectSelector(SelectSelectorConfig(options=["1", "2", "3"],mode=SelectSelectorMode.DROPDOWN,)),
                vol.Optional(CONF_PORT, default=default_port): int,
                vol.Optional(CONF_SCAN_INTERVAL, default=default_interval): int,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )


    async def async_step_hosts(self, user_input: dict[str, Any] | None = None):
        errors = {}
        count = int(self._data.get(CONF_TITAN_COUNT, 1))

        if user_input is not None:
            master = user_input["ip_master"]
            slaves = []

            if count >= 2:
                slaves.append(user_input["ip_slave_1"])
            if count >= 3:
                slaves.append(user_input["ip_slave_2"])

            try:
                session = async_get_clientsession(self.hass)

                config_param = json.dumps({"t": [606]}).replace(" ", "")
                url = (
                    f"http://{master}:{self._data.get(CONF_PORT, DEFAULT_PORT)}"
                    f"/rpc/Indevolt.GetData?config={config_param}"
                )

                async with session.post(url) as resp:
                    resp.raise_for_status()
                    data = await resp.json()

                cluster_state = int(data["606"])

                if cluster_state == 1001:
                    errors["base"] = "cluster_slave_detected"
                elif cluster_state == 1000:
                    self._data[CLUSTER_ROLE] = CLUSTER_MASTER
                elif cluster_state == 1002:
                    self._data[CLUSTER_ROLE] = CLUSTER_NO_CLUSTER
                else:
                    errors["base"] = "cannot_read_cluster_state"

            except Exception:
                errors["base"] = "cannot_connect"

            if not errors:
                self._data["cluster"] = {
                    "master": master,
                    "slaves": slaves,
                }

                if self._data[CONF_CONNECTION_MODE] == MODE_CLOUD:
                    return await self.async_step_cloud()

                return await self.async_step_responsibility()

        current_cluster = self._data.get("cluster", {})
        default_master = current_cluster.get("master", "")
        current_slaves = current_cluster.get("slaves", [])

        schema_fields = {
            vol.Required("ip_master", default=default_master): str,
        }

        if count >= 2:
            default_slave_1 = current_slaves[0] if len(current_slaves) >= 1 else ""
            schema_fields[vol.Required("ip_slave_1", default=default_slave_1)] = str
        if count >= 3:
            default_slave_2 = current_slaves[1] if len(current_slaves) >= 2 else ""
            schema_fields[vol.Required("ip_slave_2", default=default_slave_2)] = str

        return self.async_show_form(
            step_id="hosts",
            data_schema=vol.Schema(schema_fields),
            errors=errors,
        )


    async def async_step_cloud(self, user_input: dict[str, Any] | None = None):
        errors = {}

        if user_input is not None:
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            cloud_api = IzyCloudAPI(
                username=username,
                password=password,
                session=async_get_clientsession(self.hass),
            )

            try:
                token = await cloud_api.async_login()

                if not token:
                    errors["base"] = "invalid_auth"

            except Exception as err:
                _LOGGER.warning("Cloud connection error: %s", err)
                errors["base"] = "cannot_connect"

            if not errors:
                self._data.update(user_input)
                return await self.async_step_responsibility()

        default_username = self._data.get(CONF_USERNAME, "")

        return self.async_show_form(
            step_id="cloud",
            data_schema=vol.Schema({
                vol.Required(CONF_USERNAME, default=default_username): str,
                vol.Required(CONF_PASSWORD): str,
            }),
            errors=errors,
        )


    async def async_step_responsibility(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            self._data.update(user_input)
            if user_input.get(CONF_OVERRIDE_RESPONSIBILITY):
                return await self.async_step_power_override()
            return await self.async_step_calibration()

        count = int(self._data.get(CONF_TITAN_COUNT, 1))
        default_override = self._data.get(CONF_OVERRIDE_RESPONSIBILITY, False)

        return self.async_show_form(
            step_id="responsibility",
            data_schema=vol.Schema({
                vol.Required(CONF_OVERRIDE_RESPONSIBILITY, default=default_override): bool,
            }),
            description_placeholders={"count": count, "charge": CHARGE_PER_TITAN, "discharge": DISCHARGE_PER_TITAN},
        )

    async def async_step_power_override(self, user_input: dict[str, Any] | None = None):
        errors = {}
        count = int(self._data.get(CONF_TITAN_COUNT, 1))
        
        if user_input is not None:
            limit_abs = count * MAX_ABS_PER_TITAN
            if user_input[DEFAULT_MAX_CHARGE_POWER] > limit_abs or user_input[DEFAULT_MAX_DISCHARGE_POWER] > limit_abs:
                errors["base"] = "exceed_absolute_limit"
            else:
                self._data.update(user_input)
                return await self.async_step_calibration()

        default_charge = self._data.get(DEFAULT_MAX_CHARGE_POWER, count * CHARGE_PER_TITAN)
        default_discharge = self._data.get(DEFAULT_MAX_DISCHARGE_POWER, count * DISCHARGE_PER_TITAN)

        return self.async_show_form(
            step_id="power_override",
            data_schema=vol.Schema({
                vol.Required(DEFAULT_MAX_CHARGE_POWER, default=default_charge): int,
                vol.Required(DEFAULT_MAX_DISCHARGE_POWER, default=default_discharge): int,
            }),
            errors=errors,
            description_placeholders={"max_abs": str(count * MAX_ABS_PER_TITAN)}
        )

    async def async_step_calibration(self, user_input: dict[str, Any] | None = None):
        """Paramétrage du délai de confirmation de charge complète (calibration BMS)."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_summary()

        default_minutes = self._data.get(
            CONF_FULL_CHARGE_CONFIRMATION_MINUTES,
            DEFAULT_FULL_CHARGE_CONFIRMATION_MINUTES,
        )

        return self.async_show_form(
            step_id="calibration",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_FULL_CHARGE_CONFIRMATION_MINUTES,
                    default=default_minutes,
                ): vol.All(int, vol.Range(min=1, max=60)),
            }),
            description_placeholders={
                "default_minutes": str(DEFAULT_FULL_CHARGE_CONFIRMATION_MINUTES),
            },
        )

    async def async_step_summary(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            if self._is_reconfigure:
                return self._async_update_izypower_entry()
            return self._async_create_izypower_entry()

        count = int(self._data.get(CONF_TITAN_COUNT, 1))
        mode = self._data.get(CONF_CONNECTION_MODE)
        mode_label = CONNECTION_MODE_LABELS.get(mode, mode)

        cluster = self._data.get("cluster", {})
        master = cluster.get("master")
        slaves = cluster.get("slaves", [])

        charge = self._data.get(DEFAULT_MAX_CHARGE_POWER, count * CHARGE_PER_TITAN)
        discharge = self._data.get(DEFAULT_MAX_DISCHARGE_POWER, count * DISCHARGE_PER_TITAN)
        confirmation_min = self._data.get(
            CONF_FULL_CHARGE_CONFIRMATION_MINUTES,
            DEFAULT_FULL_CHARGE_CONFIRMATION_MINUTES,
        )

        summary = (
            f"### 🏠 Résumé de votre configuration\n\n"
            f"- **Mode de connexion** : {mode_label}\n"
            f"- **Nombre de Titans** : {count}\n\n"
            f"#### 🔗 Cluster\n"
            f"- Master : {master}\n"
        )

        for idx, ip in enumerate(slaves, start=1):
            summary += f"- Slave {idx} : {ip}\n"

        summary += (
            f"\n#### ⚡ Limites de puissance\n"
            f"- Charge max : **{charge} W**\n"
            f"- Décharge max : **{discharge} W**\n"
            f"\n#### 🔋 Calibration BMS\n"
            f"- Délai confirmation charge complète : **{confirmation_min} min**\n"
        )

        return self.async_show_form(
            step_id="summary",
            data_schema=vol.Schema({}),  
            description_placeholders={
                "summary_text": summary
            }
        )   
    
    def _async_create_izypower_entry(self):
        count = int(self._data[CONF_TITAN_COUNT])

        title = f"Izypower Titan Cluster ({count})"

        return self.async_create_entry(
            title=title,
            data=self._data,
            options={
                CONF_SCAN_INTERVAL: self._data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                DEFAULT_MAX_CHARGE_POWER: self._data.get(DEFAULT_MAX_CHARGE_POWER, count * CHARGE_PER_TITAN),
                DEFAULT_MAX_DISCHARGE_POWER: self._data.get(DEFAULT_MAX_DISCHARGE_POWER, count * DISCHARGE_PER_TITAN),
                CLUSTER_ROLE: self._data.get(CLUSTER_ROLE),
                CONF_FULL_CHARGE_CONFIRMATION_MINUTES: self._data.get(
                    CONF_FULL_CHARGE_CONFIRMATION_MINUTES,
                    DEFAULT_FULL_CHARGE_CONFIRMATION_MINUTES,
                ),
            },
        )

    def _async_update_izypower_entry(self):
        count = int(self._data[CONF_TITAN_COUNT])
        entry = self._get_reconfigure_entry()

        new_options = dict(entry.options)
        new_options[CONF_SCAN_INTERVAL] = self._data.get(
            CONF_SCAN_INTERVAL, entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        new_options[DEFAULT_MAX_CHARGE_POWER] = self._data.get(
            DEFAULT_MAX_CHARGE_POWER, count * CHARGE_PER_TITAN
        )
        new_options[DEFAULT_MAX_DISCHARGE_POWER] = self._data.get(
            DEFAULT_MAX_DISCHARGE_POWER, count * DISCHARGE_PER_TITAN
        )
        new_options[CLUSTER_ROLE] = self._data.get(CLUSTER_ROLE)
        new_options[CONF_FULL_CHARGE_CONFIRMATION_MINUTES] = self._data.get(
            CONF_FULL_CHARGE_CONFIRMATION_MINUTES,
            entry.options.get(
                CONF_FULL_CHARGE_CONFIRMATION_MINUTES,
                DEFAULT_FULL_CHARGE_CONFIRMATION_MINUTES,
            ),
        )

        title = f"Izypower Titan Cluster ({count})"

        return self.async_update_reload_and_abort(
            entry,
            title=title,
            data=self._data,
            options=new_options,
        )

class IzypowerOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry):
        self._entry_id = config_entry.entry_id

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        entry = self.hass.config_entries.async_get_entry(self._entry_id)

        titan_count = int(entry.data.get(CONF_TITAN_COUNT, 1))
        max_abs = titan_count * MAX_ABS_PER_TITAN

        if user_input is not None:
            if DEFAULT_MAX_CHARGE_POWER in user_input:
                user_input[DEFAULT_MAX_CHARGE_POWER] = min(
                    user_input[DEFAULT_MAX_CHARGE_POWER],
                    max_abs,
                )
            if DEFAULT_MAX_DISCHARGE_POWER in user_input:
                user_input[DEFAULT_MAX_DISCHARGE_POWER] = min(
                    user_input[DEFAULT_MAX_DISCHARGE_POWER],
                    max_abs,
                )
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=3, max=300)),

                vol.Optional(
                    DEFAULT_MAX_CHARGE_POWER,
                    default=entry.options.get(DEFAULT_MAX_CHARGE_POWER, titan_count * CHARGE_PER_TITAN),
                ): int,

                vol.Optional(
                    DEFAULT_MAX_DISCHARGE_POWER,
                    default=entry.options.get(DEFAULT_MAX_DISCHARGE_POWER, titan_count * DISCHARGE_PER_TITAN),
                ): int,

                vol.Optional(
                    CONF_FULL_CHARGE_CONFIRMATION_MINUTES,
                    default=entry.options.get(
                        CONF_FULL_CHARGE_CONFIRMATION_MINUTES,
                        DEFAULT_FULL_CHARGE_CONFIRMATION_MINUTES,
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=60)),
            }),
        )
