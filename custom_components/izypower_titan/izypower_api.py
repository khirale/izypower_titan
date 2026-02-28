import asyncio
import aiohttp
import json
import logging
from typing import Dict, Any, List

_LOGGER = logging.getLogger(__name__)

class IzypowerAPI:
    
    def __init__(self, host: str, port: int, session: aiohttp.ClientSession):
        self.host = host
        self.port = port
        self.session = session
        self.base_url = f"http://{host}:{port}/rpc"
        self.timeout = aiohttp.ClientTimeout(total=15)
    
    async def fetch_data(self, keys: List[int]) -> Dict[str, Any]:
        config_param = json.dumps({"t": keys}).replace(" ", "")
        url = f"{self.base_url}/Indevolt.GetData?config={config_param}"
        
        #_LOGGER.debug("Titan request → %s", url)

        try:
            async with self.session.post(url, timeout=self.timeout) as response:
                status = response.status
                raw_text = await response.text()

                #_LOGGER.debug("Titan response ← status=%s, raw=%s", status,  raw_text)

                if status != 200:
                    raise Exception(f"HTTP {status}: {raw_text}")

                try:
                    data = json.loads(raw_text)

                except json.JSONDecodeError as err:
                    _LOGGER.error("Titan response is NOT JSON (%s) | raw=%s", err, raw_text)
                    raise

                if not isinstance(data, dict):
                    _LOGGER.error("Titan JSON is not a dict (%s) | value=%s", type(data), data)
                    raise Exception("Invalid JSON structure")

                #_LOGGER.debug("Titan JSON parsed successfully (%d keys)", len(data))

                return data

        except asyncio.TimeoutError:
            _LOGGER.error("Titan request TIMEOUT")
            raise

        except aiohttp.ClientError as err:
            _LOGGER.error("Titan NETWORK error: %s", err)
            raise


    async def set_data(self, f: int, t: int, v: list) -> dict[str, Any]:
        config_param = json.dumps({"f": f, "t": t, "v": v}).replace(" ", "")
        url = f"{self.base_url}/Indevolt.SetData?config={config_param}"
        
        try:
            async with self.session.post(url, timeout=self.timeout) as response:
                if response.status != 200:
                    raise Exception(f"HTTP status error: {response.status}")
                return await response.json()

        except asyncio.TimeoutError:
            raise Exception("Indevolt.SetData Request timed out")
        except aiohttp.ClientError as err:
            raise Exception(f"Indevolt.SetData Network error: {err}")
    

    async def async_set_realtime_mode(self) -> dict[str, Any]:
        return await self.set_data(f=16, t=47005, v=[4])
        

    async def async_set_selfconsumed_mode(self) -> dict[str, Any]:
        return await self.set_data(f=16, t=47005, v=[1])


    async def async_charge(self, power: int, soc_limit: int, max_power: int) -> dict[str, Any]:
        if not 0 <= power <= max_power:
            raise ValueError(f"Charging power must be 0-{max_power}W, got {power}W")
        if not 0 <= soc_limit <= 100:
            raise ValueError(f"SOC limit must be 0-100%, got {soc_limit}%")
        
        return await self.set_data(f=16, t=47015, v=[1, power, soc_limit])


    async def async_discharge(self, power: int, soc_limit: int, max_power: int) -> dict[str, Any]:
        if not 0 <= power <= max_power:
            raise ValueError(f"Discharging power must be 0-{max_power}W, got {power}W")
        if not 0 <= soc_limit <= 100:
            raise ValueError(f"SOC limit must be 0-100%, got {soc_limit}%")
        
        return await self.set_data(f=16, t=47015, v=[2, power, soc_limit])


    async def async_stop(self) -> dict[str, Any]:
        return await self.set_data(f=16, t=47015, v=[0, 0, 0])


    async def async_set_working_mode(self, mode: int):
        return await self.set_data(f=16, t=47005, v=[mode])


    async def async_set_register_off_grid(self, value: int) -> dict[str, Any]:
        return await self.set_data(f=16, t=7266, v=[value])


    async def async_set_register_led(self, value: int) -> dict[str, Any]:
        return await self.set_data(f=16, t=7265, v=[value])


    async def async_set_soc_security_register(self, value: int) -> dict[str, Any]:
        from .const import SOC_SECURITY_MIN, SOC_SECURITY_MAX
        
        if not SOC_SECURITY_MIN <= value <= SOC_SECURITY_MAX:
            raise ValueError(
                f"SOC Security must be {SOC_SECURITY_MIN}-{SOC_SECURITY_MAX}%, got {value}%"
            )
        
        return await self.set_data(f=16, t=1142, v=[value])


    async def async_set_max_power_register(self, value: int, max_power: int) -> dict[str, Any]:
        if not 50 <= value <= max_power:
            raise ValueError(
                f"Max Power must be 50-{max_power}W, got {value}W"
            )
        
        return await self.set_data(f=16, t=1138, v=[value])


    async def async_set_max_discharge_power_register(self, value: int, max_power: int) -> dict[str, Any]:
        if not 0 <= value <= max_power:
            raise ValueError(
                f"Max Discharge Power must be 100-{max_power}W, got {value}W"
            )
        
        return await self.set_data(f=16, t=1147, v=[value])
