from homeassistant.const import UnitOfPower, UnitOfEnergy, PERCENTAGE
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
import logging

_LOGGER = logging.getLogger(__name__)


def is_meter_connected(coordinator) -> bool:
    data = coordinator.data or {}
    raw_value = data.get("7120")
    
    if raw_value is None:
        _LOGGER.debug("Sensor 7120 (meter_connection) not available")
        return False
    
    try:
        meter_state = int(float(raw_value))
        is_connected = (meter_state == 1000)
        
        if not is_connected:
            _LOGGER.debug(
                "Meter not connected: sensor 7120 = %s (expected 1000)",
                meter_state
            )
        
        return is_connected
        
    except (TypeError, ValueError) as err:
        _LOGGER.warning(
            "Invalid value for sensor 7120 (meter_connection): %s (%s)",
            raw_value,
            err
        )
        return False


def normalize_unit(unit: str | None):
    if not unit:
        return None

    u = str(unit).strip().lower()
    if u in ("w", "watt", "watts"):
        return UnitOfPower.WATT
    if u in ("kw", "kilowatt"):
        return UnitOfPower.KILO_WATT
    if u in ("kwh", "kilowatt-hour", "kilowatt hours"):
        return UnitOfEnergy.KILO_WATT_HOUR
    if u in ("%", "percent", "percentage"):
        return PERCENTAGE
    return unit


def map_device_class(dc: str | None):
    if not dc:
        return None

    dc = str(dc).strip().lower()
    match dc:
        case "power": return SensorDeviceClass.POWER
        case "energy": return SensorDeviceClass.ENERGY
        case "battery": return SensorDeviceClass.BATTERY
        case "energy_storage": return SensorDeviceClass.ENERGY_STORAGE
        case "voltage": return SensorDeviceClass.VOLTAGE
        case "current": return SensorDeviceClass.CURRENT
        case "temperature": return SensorDeviceClass.TEMPERATURE
        case "enum": return SensorDeviceClass.ENUM
        case _: return None


def map_state_class(sc: str | None):
    if not sc:
        return None

    sc = str(sc).strip().lower()
    match sc:
        case "measurement": return SensorStateClass.MEASUREMENT
        case "total": return SensorStateClass.TOTAL
        case "total_increasing": return SensorStateClass.TOTAL_INCREASING
        case _: return None
