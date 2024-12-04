"""Top level class for BMS devices."""
from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from homeassistant.const import (
    ATTR_DEFAULT_NAME,
    ATTR_HW_VERSION,
    ATTR_IDENTIFIERS,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    ATTR_SW_VERSION,
)
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import ATTR_SERIAL_NUMBER, DEFAULT_DEVICE_NAME, DOMAIN, MANUFACTURER

_LOGGER = logging.getLogger(__name__)


class BMSEntity(CoordinatorEntity):
    """Representation of a BMS device."""

    def __init__(
        self, coordinator: DataUpdateCoordinator, config_entry_data: Mapping[str, Any]
    ) -> None:
        """Initialise the basic device."""
        super().__init__(coordinator)
        self._config_entry_data = config_entry_data
        self.type = "device"

    @property
    def unique_id(self) -> str | None:
        """Return the unique id for this device."""
        serial = self._config_entry_data.get(ATTR_SERIAL_NUMBER)
        if serial is None:
            return None
        return f"{serial}_{self.entity_description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device specific attributes."""
        device_info = {
            ATTR_IDENTIFIERS: {(DOMAIN, self._config_entry_data[ATTR_SERIAL_NUMBER])},
            ATTR_MANUFACTURER: MANUFACTURER,
            ATTR_MODEL: self._config_entry_data[ATTR_MODEL],
            ATTR_SW_VERSION: self._config_entry_data[ATTR_SW_VERSION],
            ATTR_HW_VERSION: self._config_entry_data[ATTR_HW_VERSION],
            ATTR_MODEL_ID: self._config_entry_data[ATTR_MODEL],
            ATTR_NAME: f"{MANUFACTURER} {DEFAULT_DEVICE_NAME} {self._config_entry_data[ATTR_MODEL]}",
        }

        if ATTR_SERIAL_NUMBER in self._config_entry_data:
            device_info.ATTR_SERIAL_NUMBER = self._config_entry_data[ATTR_SERIAL_NUMBER]

        return device_info