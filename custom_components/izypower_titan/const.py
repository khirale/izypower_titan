from homeassistant.const import Platform

DOMAIN = "izypower_titan"
DEFAULT_PORT = 8080
DEFAULT_SCAN_INTERVAL = 5

DEFAULT_MAX_CHARGE_POWER = "max_charge_power"
DEFAULT_MAX_DISCHARGE_POWER = "max_discharge_power"

CONF_CONNECTION_MODE = "connection_mode"
MODE_LOCAL = "Local"
MODE_CLOUD = "Cloud"
CONNECTION_MODE_LABELS = {
    MODE_LOCAL: "MR1",
    MODE_CLOUD: "Smart IA",
}

CONF_FULL_CHARGE_CONFIRMATION_MINUTES = "full_charge_confirmation_minutes"
DEFAULT_FULL_CHARGE_CONFIRMATION_MINUTES = 10

ENTITY_SCOPE_CLUSTER = "cluster"
ENTITY_SCOPE_UNIT = "unit"

CONTROL = "selected"

CONF_TITAN_COUNT = "titan_count"
CONF_OVERRIDE_RESPONSIBILITY = "override_responsibility"

CHARGE_PER_TITAN = 800
DISCHARGE_PER_TITAN = 800
MAX_ABS_PER_TITAN = 2400

SOC_SECURITY_MIN = 5
SOC_SECURITY_MAX = 100
SOC_SECURITY_STEP = 5

CLUSTER_ROLE = "cluster_role"
CLUSTER_MASTER = "master"
CLUSTER_SLAVE = "slave"
CLUSTER_NO_CLUSTER = "no_cluster"

PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SWITCH,
]

TITAN_IDS = [
    #1,                            # Model ✅
    0,                            # Device SN ✅
    7101,                         # Working mode ✅
    1664, 1665, 1666, 1667,       # DC Input Power 1..4 ✅
    1501,                         # Total DC Output Power ✅
    2108,                         # Total AC Output Power ✅
    1502,                         # Daily Production ✅
    2101,                         # AC Input Power
    2107,                         # Total AC Input Energy ✅ Valeur Cluster
    2104,                         # Total AC Output Energy ✅Valeur Cluster
    142,                          # Rated Capacity ✅
    6000,                         # Battery Power ✅
    6001,                         # Battery State ✅
    6002,                         # Battery SOC ✅
    6009,                         # Battery level ✅
    6105,                         # Emergency Power Supply ✅
    6004,                         # Battery Daily Charging Energy ✅
    6005,                         # Battery Daily Discharging Energy ✅
    6006,                         # Battery Total Charging Energy ✅
    6007,                         # Battery Total Discharging Energy ✅
    7120,                         # Meter Connection ✅
    11016,                        # Meter Power ✅
    667,                          # Bypass Power ✅
    2098,                         # AC output ✅
    9012,                         # Battery Temperature ✅
    11019,                        # Remaining Charging Time ✅
    11020,                        # Residual Discharge Time ✅
    606,                          # Cluster Master/Slave ✅
    11009,                        # Charging Power ✅
    11011,                        # Discharging Power ✅
    2278,                         # Power Of Parallel Ac Input And Output ✅
    8100,                         # Alarm code ✅
    680,                          # Backup ✅
    7171,                         # LEDs State
    9003,                         # Battertie cycles number
    11005,                        # Battery inverter temperature
    2600,                         # Grid Voltage
    2612,                         # Grid Frequency
    11010,                        # Feed-in Power Limit 

]


ALARM_CODE_MAPPING = {
    0: "No Alarm",
    1: "AC Connection Disconnected",
    2: "Grid Connection Disconnected",
    3: "Inverter Overfrequency",
    4: "Inverter Underfrequency",
    5: "PV1-PV Input Undervoltage",
    6: "PV2-PV Input Undervoltage",
    7: "PV3-PV Input Undervoltage",
    8: "PV4-PV Input Undervoltage",
    9: "DC Side Overvoltage",
    10: "DC Side Connection Disconnected",
    11: "Ground Fault",
    12: "AC Output Short Circuit",
    13: "Inverter Overheating",
    14: "AC Input Undervoltage",
    15: "Inverter Input Short Circuit",
    16: "Inverter Undertemperature",
    17: "Off-grid Inverter Phase A Overvoltage",
    18: "Off-grid Inverter Phase A Undervoltage",
    19: "Off-grid Inverter Phase A Overcurrent/Overload",
    20: "PV Input Overvoltage",
    21: "PV Input Disconnected",
    22: "PV Module Input Short Circuit",
    23: "PV Module Low Temperature",
    24: "PV Input Reverse Polarity",
    25: "PV2-PV Input Overvoltage",
    26: "PV2-PV Input Disconnected",
    27: "PV2-PV Module Input Short Circuit",
    28: "PV2-PV Module Low Temperature",
    29: "PV2-PV Input Reverse Polarity",
    30: "PV3-PV Input Overvoltage",
    31: "PV3-PV Input Disconnected",
    32: "PV3-PV Module Input Short Circuit",
    33: "PV3-PV Module Low Temperature",
    34: "PV3-PV Input Reverse Polarity",
    35: "PV4-PV Input Overvoltage",
    36: "PV4-PV Input Disconnected",
    37: "PV4-PV Module Input Short Circuit",
    38: "PV4-PV Module Low Temperature",
    39: "PV4-PV Input Reverse Polarity",
}

WORKING_MODE_MAPPING_LOCAL = {
    0: "Outdoor Portable",
    1: "Self-consumed",
    2: "Charge/discharge schedule",
    4: "RealTime",
    5: "Charge/discharge schedule",
}

WORKING_MODE_MAPPING_CLOUD = {
    0: "Outdoor Portable",
    1: "Self-consumed",
    2: "Backup",
    3: "Schedule",
    4: "Intelligent",
    5: "Manual",
    6: "Off-grid",
    7: "Zero Export",
}

ID_META = {
    # Identité
    #1:     {"key": "model", "name": "TITAN - Model"},  # YZ-E2000G2
    0:     {"key": "device_sn", "name": "TITAN - Device SN"},
    
    # Cluster
    606:   {"key": "cluster_state", "name": "TITAN - Cluster State", "dev_class": "enum", "state_mapping": {1000: "Master", 1001: "Slave", 1002: "No Cluster"}},
    
    # Mode de fonctionnement
    7101: {"key": "working_mode", "name": "TITAN - Working Mode", "dev_class": "enum",},
    
    # PV Power
    1664:  {"key": "dc_input_power1", "name": "TITAN - DC Input Power 1", "unit": "W", "dev_class": "power", "state_class": "measurement"},
    1665:  {"key": "dc_input_power2", "name": "TITAN - DC Input Power 2", "unit": "W", "dev_class": "power", "state_class": "measurement"},
    1666:  {"key": "dc_input_power3", "name": "TITAN - DC Input Power 3", "unit": "W", "dev_class": "power", "state_class": "measurement"},
    1667:  {"key": "dc_input_power4", "name": "TITAN - DC Input Power 4", "unit": "W", "dev_class": "power", "state_class": "measurement"},
    
    # Puissance
    1501:  {"key": "total_dc_output_power", "name": "TITAN - Total DC Output Power", "unit": "W", "dev_class": "power", "state_class": "measurement"},
    2108:  {"key": "total_ac_output_power", "name": "TITAN - Total AC Output Power", "unit": "W", "dev_class": "power", "state_class": "measurement"},
    2098:  {"key": "ac_output_power", "name": "TITAN - AC output Power", "unit": "W", "dev_class": "power", "state_class": "measurement"},
    2278:  {"key": "ac_input_output", "name": "TITAN - AC Input And Output", "unit": "W", "dev_class": "power", "state_class": "measurement"},
    11010: {"key": "feedin_power_limit", "name": "TITAN - Feed-in Power Limit", "unit": "W", "dev_class": "power", "state_class": "measurement"},
    
    # Production/Energie
    1502:  {"key": "daily_production", "name": "TITAN - Daily Production", "unit": "kWh", "dev_class": "energy", "state_class": "total"},
    2101:  {"key": "ac_input_power", "name": "TITAN - AC Input Power", "unit": "W", "dev_class": "power", "state_class": "measurement"},
    2107:  {"key": "total_ac_input_energy", "name": "TITAN - Total AC Input Energy", "unit": "kWh", "dev_class": "energy", "state_class": "total_increasing"},
    2104:  {"key": "total_ac_output_energy", "name": "TITAN - Total AC Output Energy", "unit": "kWh", "dev_class": "energy", "state_class": "total_increasing"},
    142:   {"key": "rated_capacity", "name": "TITAN - Rated Capacity", "unit": "kWh", "dev_class": "energy_storage", "state_class": None},
    
    # Batterie TITAN principale
    6000:  {"key": "battery_power", "name": "TITAN - Battery Power", "unit": "W", "dev_class": "power", "state_class": "measurement"},
    6001:  {"key": "battery_state", "name": "TITAN - Battery State", "dev_class": "enum", "state_mapping": {1000: "Static", 1001: "Charging", 1002: "Discharging"}},
    6002:  {"key": "battery_soc", "name": "TITAN - Pile Average", "unit": "%", "dev_class": "battery", "state_class": "measurement"},
    6009:  {"key": "battery_titan_level", "name": "TITAN - Battery %", "unit": "%", "dev_class": "battery", "state_class": "measurement"},
    11009:  {"key": "charging_power", "name": "TITAN - Charging Power", "unit": "W", "dev_class": "power", "state_class": "measurement"},
    11011:  {"key": "discharging_power", "name": "TITAN - Discharging Power", "unit": "W", "dev_class": "power", "state_class": "measurement"},
    9003: {"key": "battery_cycle", "name": "Titan - Battery Cycles", "unit": None, "dev_class": None, "state_class": None},
    2600:  {"key": "grid_voltage", "name": "TITAN - Grid Voltage", "unit": "V", "dev_class": "voltage", "state_class": "measurement"},
    2612:  {"key": "grid_frequency", "name": "TITAN - Grid Frequency", "unit": "Hz", "dev_class": "frequency", "state_class": "measurement"},
    
    # Energie batterie
    6105:  {"key": "emergency_power_supply", "name": "TITAN - Battery SOC", "unit": "%", "state_class": "measurement"},
    6004:  {"key": "battery_daily_charging_energy", "name": "TITAN - Battery Daily Charging Energy", "unit": "kWh", "dev_class": "energy", "state_class": "total"},
    6005:  {"key": "battery_daily_discharging_energy", "name": "TITAN - Battery Daily Discharging Energy", "unit": "kWh", "dev_class": "energy", "state_class": "total"},
    6006:  {"key": "battery_total_charging_energy", "name": "TITAN - Battery Total Charging Energy", "unit": "kWh", "dev_class": "energy", "state_class": "total_increasing"},
    6007:  {"key": "battery_total_discharging_energy", "name": "TITAN - Battery Total Discharging Energy", "unit": "kWh", "dev_class": "energy", "state_class": "total_increasing"},
    
    # Système
    7120:  {"key": "meter_connection", "name": "TITAN - Meter Connection", "dev_class": "enum", "state_mapping": {1000: "ON", 1001: "OFF"}},
    11016: {"key": "meter_power", "name": "TITAN - Meter Power", "unit": "W", "dev_class": "power", "state_class": "measurement"},
    667:   {"key": "bypass_power", "name": "TITAN - Bypass Power", "unit": "W", "dev_class": "power", "state_class": "measurement"},
    8100:  {"key": "alarm_code", "name": "TITAN - Alarm", "dev_class": "enum", "state_mapping": ALARM_CODE_MAPPING},
    680:   {"key": "backup", "name": "TITAN - Backup State", "dev_class": "enum", "state_mapping": {0: "OFF", 1: "ON"}},
    7171:  {"key": "leds", "name": "TITAN - LEDs State", "dev_class": "enum", "state_mapping": {0: "OFF", 1: "ON"}},
    
    # Températures
    9012:  {"key": "battery_temperature", "name": "TITAN - Battery Temperature", "unit": "°C", "dev_class": "temperature", "state_class": "measurement"},
    11005: {"key": "battery_inverter_temperature", "name": "TITAN - Inverter Temperature", "unit": "°C", "dev_class": "temperature", "state_class": "measurement"},

    # Temps de charge/décharge
    11019: {"key": "remaining_charging_time", "name": "TITAN - Remaining Charging Time", "unit": "min", "state_class": "measurement"},
    11020: {"key": "residual_discharge_time", "name": "TITAN - Residual Discharge Time", "unit": "min", "state_class": "measurement"},
}


LINK_ID_GROUPS = [
    [9032, 9016, 9030, 9019],
    [9051, 9035, 9049, 9038],
    [9070, 9054, 9068, 9057],
    [9165, 9149, 9163,9152],
    [9218, 9202, 9216,9205],
]


LINK_ID_META = {
    9032: {"key": "link_batt_sn", "name": "LINK - SN", "unit": None, "dev_class": None, "state_class": None},
    9019: {"key": "link_batt_cycle", "name": "LINK - Cycles", "unit": None, "dev_class": None, "state_class": None},
    9016: {"key": "link_batt_soc", "name": "LINK - SOC", "unit": "%", "dev_class": "battery", "state_class": "measurement"},
    #9020: {"key": "link_batt_voltage", "name": "LINK - Voltage", "unit": "V", "dev_class": "voltage", "state_class": "measurement"},
    #19173: {"key": "link_batt_current", "name": "LINK - Current", "unit": "A", "dev_class": "current", "state_class": "measurement"},
    9030: {"key": "link_batt_temperature", "name": "LINK - Temperature", "unit": "°C", "dev_class": "temperature", "state_class": "measurement"},

    9051: {"key": "link_batt_sn", "name": "LINK - SN", "unit": None, "dev_class": None, "state_class": None},
    9038: {"key": "link_batt_cycle", "name": "LINK - Cycles", "unit": None, "dev_class": None, "state_class": None},
    9035: {"key": "link_batt_soc", "name": "LINK - SOC", "unit": "%", "dev_class": "battery", "state_class": "measurement"},
    #9039: {"key": "link_batt_voltage", "name": "LINK - Voltage", "unit": "V", "dev_class": "voltage", "state_class": "measurement"},
    #19174: {"key": "link_batt_current", "name": "LINK - Current", "unit": "A", "dev_class": "current", "state_class": "measurement"},
    9049: {"key": "link_batt_temperature", "name": "LINK - Temperature", "unit": "°C", "dev_class": "temperature", "state_class": "measurement"},

    9070: {"key": "link_batt_sn", "name": "LINK - SN", "unit": None, "dev_class": None, "state_class": None},
    9057: {"key": "link_batt_cycle", "name": "LINK - Cycles", "unit": None, "dev_class": None, "state_class": None},
    9054: {"key": "link_batt_soc", "name": "LINK - SOC", "unit": "%", "dev_class": "battery", "state_class": "measurement"},
    #9058: {"key": "link_batt_voltage", "name": "LINK - Voltage", "unit": "V", "dev_class": "voltage", "state_class": "measurement"},
    #19175: {"key": "link_batt_current", "name": "LINK - Current", "unit": "A", "dev_class": "current", "state_class": "measurement"},
    9068: {"key": "link_batt_temperature", "name": "LINK - Temperature", "unit": "°C", "dev_class": "temperature", "state_class": "measurement"},

    9165: {"key": "link_batt_sn", "name": "LINK - SN", "unit": None, "dev_class": None, "state_class": None},
    9152: {"key": "link_batt_cycle", "name": "LINK - Cycles", "unit": None, "dev_class": None, "state_class": None},
    9149: {"key": "link_batt_soc", "name": "LINK - SOC", "unit": "%", "dev_class": "battery", "state_class": "measurement"},
    #9153: {"key": "link_batt_voltage", "name": "LINK - Voltage", "unit": "V", "dev_class": "voltage", "state_class": "measurement"},
    #19176: {"key": "link_batt_current", "name": "LINK - Current", "unit": "A", "dev_class": "current", "state_class": "measurement"},
    9163: {"key": "link_batt_temperature", "name": "LINK - Temperature", "unit": "°C", "dev_class": "temperature", "state_class": "measurement"},

    9218: {"key": "link_batt_sn", "name": "LINK - SN", "unit": None, "dev_class": None, "state_class": None},
    9205: {"key": "link_batt_cycle", "name": "LINK - Cycles", "unit": None, "dev_class": None, "state_class": None},
    9202: {"key": "link_batt_soc", "name": "LINK - SOC", "unit": "%", "dev_class": "battery", "state_class": "measurement"},
    #9206: {"key": "link_batt_voltage", "name": "LINK - Voltage", "unit": "V", "dev_class": "voltage", "state_class": "measurement"},
    #19177: {"key": "link_batt_current", "name": "LINK - Current", "unit": "A", "dev_class": "current", "state_class": "measurement"},
    9216: {"key": "link_batt_temperature", "name": "LINK - Temperature", "unit": "°C", "dev_class": "temperature", "state_class": "measurement"},
}
