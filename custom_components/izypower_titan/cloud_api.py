import asyncio
import aiohttp
import json
import logging
import time
import jwt
from typing import Dict, Any

_LOGGER = logging.getLogger(__name__)

class IzyCloudAPI:
    
    def __init__(self, username, password, session: aiohttp.ClientSession):
        self.username = username
        self.password = password
        self.session = session
        self.base_url = "http://application.izypowercloud.fr/photo_voltaic/api"
        self.token = None
        self.timeout = aiohttp.ClientTimeout(total=15)
        
        self.headers_base = {
            "app-platform": "izy",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Linux; Android 16; Pixel 10a)"
        }

    @property
    def battery_url(self) -> str:
        return f"{self.base_url}/v2/device/yz/battery"

    async def async_login(self) -> str | None:
        url = f"{self.base_url}/login"
        payload = {"username": self.username, "password": self.password}
        
        try:
            async with self.session.post(url, json=payload, headers=self.headers_base, timeout=self.timeout) as response:
                data = await response.json()
                
                if response.status != 200:
                    _LOGGER.error("Erreur login Cloud: Status %s - Réponse: %s", response.status, data)
                    self.token = None
                    return None

                token = (
                    data.get("data", {}).get("token") or 
                    data.get("token") or 
                    data.get("data", {}).get("accessToken") or 
                    data.get("accessToken")
                )

                self.token = token

                if self.token:
                    _LOGGER.info("✅ Authentification Cloud réussie")
                else:
                    _LOGGER.error("❌ Login réussi mais impossible de trouver le token dans le JSON: %s", data)
                
                return self.token

        except Exception as err:
            _LOGGER.error("❌ Erreur critique de connexion au Cloud : %s", err)
            self.token = None
            return None

    def __repr__(self) -> str:
        return f"IzyCloudAPI(username={self.username!r}, password=***)"

    def is_token_valid(self) -> bool:
        if not self.token:
            return False
        try:
            decoded = jwt.decode(self.token, options={"verify_signature": False})
            return decoded.get("exp", 0) > (time.time() - 60)
        except Exception:
            return False

    async def async_get_headers(self) -> Dict[str, str]:
        if not self.is_token_valid():
            await self.async_login()
        
        headers = self.headers_base.copy()
        if self.token:
            headers["x-tts-access-token"] = self.token
        return headers

    async def async_set_discharge_power(self, device_id: str, max_out: int, is_cluster: bool | None = None) -> Dict[str, Any]:
        url = f"{self.battery_url}/power/{device_id}"
        payload = {"max_out_power": max_out, "type": "out", "isCluster": bool(is_cluster)}
        headers = await self.async_get_headers()
        async with self.session.post(url, json=payload, headers=headers, timeout=self.timeout) as resp:
            return await resp.json()

    async def async_set_charge_power(self, device_id: str, max_in: int, is_cluster: bool | None = None) -> Dict[str, Any]:
        url = f"{self.battery_url}/power/{device_id}"
        payload = {"max_in_power": max_in, "type": "in", "isCluster": bool(is_cluster)}
        headers = await self.async_get_headers()
        async with self.session.post(url, json=payload, headers=headers, timeout=self.timeout) as resp:
            return await resp.json()

    async def async_cloud_manual_charge(self, device_id: str, power_watts: int) -> Dict[str, Any]:
        headers = await self.async_get_headers()

        url_mode = f"{self.battery_url}/mode/{device_id}"
        await self.session.post(url_mode, json={"ctr_mode": 1}, headers=headers, timeout=self.timeout)

        url_val = f"{self.battery_url}/manual_mode_value/{device_id}"
        payload_power = {"mode": 1, "power": power_watts}
        async with self.session.post(url_val, json=payload_power, headers=headers, timeout=self.timeout) as resp:
            return await resp.json()

    async def async_cloud_manual_standby(self, device_id: str) -> Dict[str, Any]:
        headers = await self.async_get_headers()
        url_mode = f"{self.battery_url}/mode/{device_id}"
        await self.session.post(url_mode, json={"ctr_mode": 1}, headers=headers, timeout=self.timeout)

        url_val = f"{self.battery_url}/manual_mode_value/{device_id}"
        payload_power = {"mode": 0, "power": 0}
        async with self.session.post(url_val, json=payload_power, headers=headers, timeout=self.timeout) as resp:
            return await resp.json()

    async def async_cloud_manual_discharge(self, device_id: str, power_watts: int) -> Dict[str, Any]:
        headers = await self.async_get_headers()

        url_mode = f"{self.battery_url}/mode/{device_id}"
        await self.session.post(url_mode, json={"ctr_mode": 1}, headers=headers, timeout=self.timeout)

        url_val = f"{self.battery_url}/manual_mode_value/{device_id}"
        payload_power = {"mode": 2, "power": power_watts}
        async with self.session.post(url_val, json=payload_power, headers=headers, timeout=self.timeout) as resp:
            return await resp.json()

    async def async_intelligent_mode(self, device_id: str) -> Dict[str, Any]:
        url = f"{self.battery_url}/mode/{device_id}"
        headers = await self.async_get_headers()
        async with self.session.post(url, json={"ctr_mode": 0}, headers=headers, timeout=self.timeout) as resp:
            return await resp.json()

