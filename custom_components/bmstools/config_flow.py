"""Config flow for BMS Tools integration."""
from __future__ import annotations

import logging
from typing import Any, Mapping

from bmstools.jbd.jbd import JBD, BaseReg, BMSError
from serial import Serial, SerialException
import serial.tools.list_ports
import voluptuous as vol

from homeassistant import config_entries, core
from homeassistant.const import ATTR_HW_VERSION, ATTR_MODEL, ATTR_SW_VERSION, CONF_PORT
from homeassistant.data_entry_flow import FlowResult

from .const import (
    ATTR_SERIAL_NUMBER,
    DEFAULT_INTEGRATION_TITLE,
    DOMAIN,
    JBD_BASIC_FIRMWARE_VERSION,
    JBD_REG_DEVICE_NAME,
    JBD_REG_SERIAL_NUM,
)

_LOGGER = logging.getLogger(__name__)

MAX_CONNECTION_ATTEMPTS = 2


def connect_and_read_device_info(
    hass: core.HomeAssistant, data: Mapping[str, Any]
) -> dict[str, str]:
    """Validate the user input allows us to connect.

    Data has the keys from DATA_SCHEMA with values provided by the user.
    """
    com_port = data[CONF_PORT]
    _LOGGER.debug("Intitialising com port=%s", com_port)
    device_info = {}
    # Often the connection doesn't succeed on the first attempt, but on the second.
    # Maybe some kind of sleep behavior is involved.
    attempt = 1
    while attempt <= MAX_CONNECTION_ATTEMPTS:
        try:
            ser = Serial()
            ser.port = com_port
            client = JBD(ser)
            client.open()
            device_info[ATTR_SERIAL_NUMBER] = client.readReg(JBD_REG_SERIAL_NUM).get(
                JBD_REG_SERIAL_NUM
            )
            basic_info = client.readBasicInfo()
            device_info[ATTR_SW_VERSION] = basic_info[JBD_BASIC_FIRMWARE_VERSION]
            device_info[
                ATTR_HW_VERSION
            ] = f"{basic_info['year']}.{basic_info['month']}.{basic_info['day']}"
            device_info[ATTR_MODEL] = client.readReg(JBD_REG_DEVICE_NAME).get(
                JBD_REG_DEVICE_NAME
            )
            _LOGGER.debug("Returning device info=%s", device_info)
            break
        except BMSError as err:
            _LOGGER.warning(
                "Could not connect to device=%s, Attempt=%i", com_port, attempt
            )
            if attempt == MAX_CONNECTION_ATTEMPTS:
                raise err
        finally:
            # This method determines internally if the connection is open and needs to be closed
            client.close()
            attempt += 1

    return device_info


def scan_comports() -> tuple[list[str] | None, str | None]:
    """Find and store available COM ports for the GUI dropdown."""
    com_ports = serial.tools.list_ports.comports(include_links=True)
    com_ports_list = []
    for port in com_ports:
        com_ports_list.append(port.device)
        _LOGGER.debug("COM port option: %s", port.device)
    if len(com_ports_list) > 0:
        return com_ports_list, com_ports_list[0]
    _LOGGER.warning("No COM ports found")
    return None, None


class BMSToolsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for BMS Tools."""

    VERSION = 1

    def __init__(self):
        """Initialise the config flow."""
        self.init_info = None
        self._com_ports_list = None
        self._default_com_port = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initialised by the user."""
        _LOGGER.debug(f"Step user: {user_input}")
        return await self.async_step_init()

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        """Handle the first step, which is selecting the serial port."""
        _LOGGER.debug(f"Step init: {user_input}")

        errors = {}
        if self._com_ports_list is None:
            result = await self.hass.async_add_executor_job(scan_comports)
            self._com_ports_list, self._default_com_port = result
            if self._default_com_port is None:
                return self.async_abort(reason="no_serial_ports")

        # Handle the initial step.
        if user_input is not None:
            # Check if the port is already configured
            for existing_entry in self.hass.config_entries.async_entries(DOMAIN):
                if existing_entry.data[CONF_PORT] == user_input[CONF_PORT]:
                    return self.async_abort(reason="port_already_configured")

            # Try to connect and read device info
            try:
                self.init_info = await self.hass.async_add_executor_job(
                    connect_and_read_device_info, self.hass, user_input
                )
            except SerialException as error:
                if error.errno == 19:  # No such device.
                    errors["base"] = "invalid_serial_port"
                else:
                    errors["base"] = "cannot_open_serial_port"
                _LOGGER.exception("Cannot open serial port %s", user_input[CONF_PORT])
            except BMSError:  # There is no further error info in the exception
                errors["base"] = "cannot_connect"
                _LOGGER.error(
                    "Unable to communicate with BMS at %s", user_input[CONF_PORT]
                )
            else:
                self.init_info.update(user_input)
                return await self.async_step_serial_number()

        # If no user input, must be first pass through the config.
        data_schema = {
            vol.Required(CONF_PORT, default=self._default_com_port): vol.In(
                self._com_ports_list
            ),
        }

        # Show initial form.
        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(data_schema), errors=errors
        )

    async def async_step_serial_number(self, user_input: dict[str, Any] | None = None):
        """Handle the optional step of assigning a locally unique serial number if none is present."""
        _LOGGER.debug(f"Step serial number: {user_input}")
        errors = {}
        # Check if the user just gave consent to write serial number
        if user_input is not None:
            if user_input["consent"]:
                new_serial_num = self.get_next_available_serial_number()
                if new_serial_num:
                    # Assign the BMS a new unique serial number
                    self.write_serial_number(new_serial_num)
                    self.init_info[ATTR_SERIAL_NUMBER] = new_serial_num
                else:
                    # No more available serial numbers, maximum amount is 65535 (unsigned 16 bit int)
                    self.async_abort(reason="serial_numbers_exhausted")
            else:
                errors["base"] = "must_give_consent"

        # Check if the device already got a serial number
        if self.init_info[ATTR_SERIAL_NUMBER] == 0:
            # No, we have to assign one, but the user is asked for consent first
            data_schema = {
                vol.Required("consent", default=False): bool,
            }
            return self.async_show_form(
                step_id="serial_number",
                data_schema=vol.Schema(data_schema),
                errors=errors,
            )
        else:
            # Yes, check for duplicate
            for existing_entry in self.hass.config_entries.async_entries(DOMAIN):
                if (
                    existing_entry.data[ATTR_SERIAL_NUMBER]
                    == self.init_info[ATTR_SERIAL_NUMBER]
                ):
                    return self.async_abort(reason="device_already_configured")

        return self.async_create_entry(
            title=DEFAULT_INTEGRATION_TITLE, data=self.init_info
        )

    def get_next_available_serial_number(self):
        """Determine the next available locally unique serial number."""

        taken_serial_nums = []
        for existing_entry in self.hass.config_entries.async_entries(DOMAIN):
            taken_serial_nums.append(existing_entry[ATTR_SERIAL_NUMBER])

        for serial_number in range(1, 65536):
            if serial_number not in taken_serial_nums:
                return serial_number

        return None

    def write_serial_number(self, serial_number):
        """Write the serial number to the EEPROM of the device."""
        try:
            ser = Serial()
            ser.port = self.init_info[CONF_PORT]
            client = JBD(ser)
            serial_num_reg: BaseReg = client.eeprom_reg_by_regname.get(
                "serial_num", None
            )
            serial_num_reg.set("serial_num", serial_number)
            client.writeReg(serial_num_reg)
            _LOGGER.debug("Wrote serial number %s", serial_number)
        except BMSError:
            _LOGGER.error("Could not connect to device=%s", self.init_info[CONF_PORT])
