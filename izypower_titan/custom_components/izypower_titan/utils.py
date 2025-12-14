from homeassistant.const import UnitOfPower, UnitOfEnergy, PERCENTAGE
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass


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
    return unit  # fallback (par exemple °C, V, etc.)


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