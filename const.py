"""Constants for the BMS Tools integration."""

DOMAIN = "bmstools"

MIN_ADDRESS = 2
MAX_ADDRESS = 63
DEFAULT_ADDRESS = 2

DEFAULT_INTEGRATION_TITLE = "BMS Tools"
DEFAULT_DEVICE_NAME = "Battery Management System"

DEVICES = "devices"
MANUFACTURER = "JBD"

ATTR_DEVICE_ID = "device_id"
ATTR_SERIAL_NUMBER = "serial_number"

HASS_DATA_COORDINATOR = "coordinator"
HASS_DATA_CLIENT = "client"

COORDINATOR_DATA_BASIC_INFO = "basic_info"
COORDINATOR_DATA_CELL_INFO = "cell_info"

# JBD registers
JBD_REG_SERIAL_NUM = "serial_num"
JBD_REG_DEVICE_NAME = "device_name"

# JBD basic info keys
# Constant
JBD_BASIC_FIRMWARE_VERSION = "version"
JBD_BASIC_BATTERY_CAPACITY = "full_cap"
# Variable
JBD_BASIC_CYCLE_COUNT = "cycle_cnt"
JBD_BASIC_BATTERY_SOC = "cur_cap"
JBD_BASIC_BATTERY_VOLTAGE = "pack_mv"
JBD_BASIC_BATTERY_CURRENT = "pack_ma"
