"""The BMS Tools integration."""
from datetime import timedelta
import logging
from typing import Dict

from bmstools.jbd.jbd import JBD, BMSError
from serial import Serial

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PORT, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .config_flow import connect_and_read_device_info
from .const import (
    ATTR_SERIAL_NUMBER,
    COORDINATOR_DATA_BASIC_INFO,
    COORDINATOR_DATA_CELL_INFO,
    DOMAIN,
    HASS_DATA_CLIENT,
    HASS_DATA_COORDINATOR,
)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR, Platform.SWITCH]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up BMS Tools from a config entry."""
    device_info = await hass.async_add_executor_job(
        connect_and_read_device_info, hass, entry.data
    )
    
    # Validation check
    if not device_matches_entry(device_info, entry):
        # TODO changed behavior from failing to warning here, because BMS seems to suddenly lose serial number after some time
        _LOGGER.warning(
            f'Device serial number "{device_info[ATTR_SERIAL_NUMBER]}" does not match serial number "{entry.data[ATTR_SERIAL_NUMBER]}" in config entry!'
        )

    # TODO how to update config entry or device info shown?
    # update_device_info_in_config_entry(device_info, entry)

    # Initialize client instance
    com_port = entry.data[CONF_PORT]
    serial_client = Serial()
    serial_client.port = com_port
    client = JBD(serial_client, timeout=1, debug=False)

    async def async_update_data() -> dict:
        """Fetch data from BMS asynchronously."""

        def sync_update_data() -> dict:
            """Fetch data from BMS synchronously."""
            _LOGGER.debug("Updating...")
            try:
                client.open()
                basic_info = client.readBasicInfo()
                cell_info = client.readCellInfo()
            finally:
                client.close()
            _LOGGER.debug(basic_info)
            _LOGGER.debug(cell_info)
            return {
                COORDINATOR_DATA_BASIC_INFO: basic_info,
                COORDINATOR_DATA_CELL_INFO: cell_info,
            }

        try:
            return await hass.async_add_executor_job(sync_update_data)
        except BMSError:
            raise UpdateFailed("BMS communication error")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="BMS Tools",
        update_method=async_update_data,
        update_interval=timedelta(seconds=1),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        HASS_DATA_COORDINATOR: coordinator,
        HASS_DATA_CLIENT: client,
    }

    hass.config_entries.async_setup_platforms(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Ensure that client is closed
    client: JBD = hass.data[DOMAIN][entry.entry_id][HASS_DATA_CLIENT]
    client.close()

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


def device_matches_entry(
    device_info: Dict[str, str], config_entry: ConfigEntry
) -> bool:
    """Check if device info matches config entry."""
    return device_info[ATTR_SERIAL_NUMBER] == config_entry.data[ATTR_SERIAL_NUMBER]


# def update_device_info_in_config_entry(
#     device_info: dict[str, str], config_entry: ConfigEntry
# ):
#     """."""
#     config_entry.data[ATTR_SW_VERSION] = device_info[ATTR_SW_VERSION]
#     # This shouldn't change but it could be changed by other tools
#     config_entry.data[ATTR_HW_VERSION] = device_info[ATTR_HW_VERSION]
