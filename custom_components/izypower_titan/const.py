from homeassistant.const import Platform

DOMAIN = "izypower_titan"
DEFAULT_PORT = 8080
DEFAULT_SCAN_INTERVAL = 5

DEFAULT_MAX_CHARGE_POWER = 1200  # Watts
DEFAULT_MAX_DISCHARGE_POWER = 800  # Watts

PLATFORMS = [
    Platform.SENSOR
]

TITAN_IDS = [
    1,      # Model ✅
    0,      # Device SN ✅
    7101,   # Working mode ✅
    1664, 1665, 1666, 1667,       # DC Input Power 1..4 ✅
    1501,                          # Total DC Output Power ✅
    2108,                          # Total AC Output Power ✅
    1502,                          # Daily Production ✅
    1505,                          # Cumulative Production ✅
    2101,                          # Total AC Input Power ✅
    2107,                          # Total AC Input Energy ✅
    142,                           # Rated Capacity ✅
    6000,                          # Battery Power ✅
    6001,                          # Battery State ✅
    6002,                          # Battery SOC ✅
    6009,                          # Battery level ✅
    6105,                          # Emergency Power Supply ✅
    6004,                          # Battery Daily Charging Energy ✅
    6005,                          # Battery Daily Discharging Energy ✅
    6006,                          # Battery Total Charging Energy ✅
    6007,                          # Battery Total Discharging Energy ✅
    7120,                          # Meter Connection ✅
    11016,                         # Meter Power ✅
    667,                           # Bypass Power ✅
    2098,                          # AC output ✅
    9077,                          # Battery Temperature ✅
    11019,                         # Remaining Charging Time ✅
    11020,                         # Residual Discharge Time ✅
    11041,                         # Battery Temperature 1 ✅
    9100,                          # Battery Temperature 2 ✅
    9084,                          # Battery Temperature 3 ✅
    606,                           # Cluster Master/Slave ✅
    11009,                         # Charging Power ✅
    11011                          # Discharging Power ✅
]

ID_META = {
    # Identité
    1:     {"key": "model", "name": "TITAN - Model"},  # YZ-E2000G2
    0:     {"key": "device_sn", "name": "TITAN - Device SN"},
    
    # Cluster
    606:   {"key": "cluster_state", "name": "TITAN - Cluster State", "dev_class": "enum", "state_mapping": {1000: "Master", 1001: "Slave", 1002: "No Cluster", -1: "Unknown"}},
    
    # Mode de fonctionnement
    7101:  {"key": "working_mode", "name": "TITAN - Working Mode","dev_class": "enum", "state_mapping": {0: "Standby", 1: "Self-consumed", 2: "Backup", 3: "Schedule", 4: "Intelligent", 5: "Manual", 6: "Off-grid", 7: "Zero Export", -1: "Unknown"}},
    
    # PV Power
    1664:  {"key": "dc_input_power1", "name": "TITAN - DC Input Power 1", "unit": "W", "dev_class": "power", "state_class": "measurement"},
    1665:  {"key": "dc_input_power2", "name": "TITAN - DC Input Power 2", "unit": "W", "dev_class": "power", "state_class": "measurement"},
    1666:  {"key": "dc_input_power3", "name": "TITAN - DC Input Power 3", "unit": "W", "dev_class": "power", "state_class": "measurement"},
    1667:  {"key": "dc_input_power4", "name": "TITAN - DC Input Power 4", "unit": "W", "dev_class": "power", "state_class": "measurement"},
    
    # Puissance
    1501:  {"key": "total_dc_output_power", "name": "TITAN - Total DC Output Power", "unit": "W", "dev_class": "power", "state_class": "measurement"},
    2108:  {"key": "total_ac_output_power", "name": "TITAN - Total AC Output Power", "unit": "W", "dev_class": "power", "state_class": "measurement"},
    2098:  {"key": "ac_output_power", "name": "TITAN - AC output", "unit": "W", "dev_class": "power", "state_class": "measurement"},
    
    # Production/Energie
    1502:  {"key": "daily_production", "name": "TITAN - Daily Production", "unit": "kWh", "dev_class": "energy", "state_class": "total"},
    1505: {"key": "cumulative_production", "name": "TITAN - Cumulative Production", "unit": "kWh", "dev_class": "energy", "state_class": "total"},  # ← total au lieu de total_increasing
    2101:  {"key": "total_ac_input_power", "name": "TITAN - Total AC Input Power", "unit": "W", "dev_class": "power", "state_class": "measurement"},
    2107:  {"key": "total_ac_input_energy", "name": "TITAN - Total AC Input Energy", "unit": "kWh", "dev_class": "energy", "state_class": "total_increasing"},
    142:   {"key": "rated_capacity", "name": "TITAN - Rated Capacity", "unit": "kWh", "dev_class": "energy_storage", "state_class": None},
    
    # Batterie TITAN principale
    6000:  {"key": "battery_power", "name": "TITAN - Battery Power", "unit": "W", "dev_class": "power", "state_class": "measurement"},
    6001:  {"key": "battery_state", "name": "TITAN - Battery State", "dev_class": "enum", "state_mapping": {1000: "Static", 1001: "Charging", 1002: "Discharging", -1:"Unknown"}},
    6002:  {"key": "battery_soc", "name": "TITAN - Pile Average", "unit": "%", "dev_class": "battery", "state_class": "measurement"},
    6009:  {"key": "battery_titan_level", "name": "TITAN - Battery %", "unit": "%", "dev_class": "battery", "state_class": "measurement"},
    11009:  {"key": "charging_power", "name": "TITAN - Charging Power", "unit": "W", "dev_class": "power", "state_class": "measurement"},
    11011:  {"key": "discharging_power", "name": "TITAN - Discharging Power", "unit": "W", "dev_class": "power", "state_class": "measurement"},
    
    # Battery LINKS

    
    # Energie batterie
    6105:  {"key": "emergency_power_supply", "name": "TITAN - Battery SOC", "unit": "%", "state_class": "measurement"},
    6004:  {"key": "battery_daily_charging_energy", "name": "TITAN - Battery Daily Charging Energy", "unit": "kWh", "dev_class": "energy", "state_class": "total"},
    6005:  {"key": "battery_daily_discharging_energy", "name": "TITAN - Battery Daily Discharging Energy", "unit": "kWh", "dev_class": "energy", "state_class": "total"},
    6006:  {"key": "battery_total_charging_energy", "name": "TITAN - Battery Total Charging Energy", "unit": "kWh", "dev_class": "energy", "state_class": "total_increasing"},
    6007:  {"key": "battery_total_discharging_energy", "name": "TITAN - Battery Total Discharging Energy", "unit": "kWh", "dev_class": "energy", "state_class": "total_increasing"},
    
    # Système
    7120:  {"key": "meter_connection", "name": "TITAN - Meter Connection", "dev_class": "enum", "state_mapping": {1000: "ON", 1001: "OFF", -1:"Unknown"}},
    11016: {"key": "meter_power", "name": "TITAN - Meter Power", "unit": "W", "dev_class": "power", "state_class": "measurement"},
    667:   {"key": "bypass_power", "name": "TITAN - Bypass Power", "unit": "W", "dev_class": "power", "state_class": "measurement"},
    
    # Températures (4 sensors)
    9077:  {"key": "battery_temperature", "name": "TITAN - Battery Temperature", "unit": "°C", "dev_class": "temperature", "state_class": "measurement"},
    11041: {"key": "battery_temperature_1", "name": "TITAN - Battery Temperature 1", "unit": "°C", "dev_class": "temperature", "state_class": "measurement"},  # 33°C
    9100:  {"key": "battery_temperature_2", "name": "TITAN - Battery Temperature 2", "unit": "°C", "dev_class": "temperature", "state_class": "measurement"},  # 26°C
    9084:  {"key": "battery_temperature_3", "name": "TITAN - Battery Temperature 3", "unit": "°C", "dev_class": "temperature", "state_class": "measurement"},  # 0°C
    
    # Temps de charge/décharge
    11019: {"key": "remaining_charging_time", "name": "TITAN - Remaining Charging Time", "unit": "min", "state_class": "measurement"},  # 9999 min
    11020: {"key": "residual_discharge_time", "name": "TITAN - Residual Discharge Time", "unit": "min", "state_class": "measurement"},  # 304 min
}




