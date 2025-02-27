"""Support for BMS Tools switches."""
from __future__ import annotations

import logging
from typing import Any, Mapping

from bmstools.jbd.jbd import JBD

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import ToggleEntity, ToggleEntityDescription
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .device import BMSEntity
from .sensor import JBDBasicInfoSensor
from .const import (
    COORDINATOR_DATA_BASIC_INFO,
    DOMAIN,
    HASS_DATA_CLIENT,
    HASS_DATA_COORDINATOR,
)

_LOGGER = logging.getLogger(__name__)

# Charging and discharging switch must be updated sequentially
PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Switch platform for BMS Tools."""
    entities: list[ToggleEntity] = []

    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        HASS_DATA_COORDINATOR
    ]
    client: JBD = hass.data[DOMAIN][config_entry.entry_id][HASS_DATA_CLIENT]

    entities.append(JBDChargeToggle(coordinator, client, config_entry.data))
    entities.append(JBDDischargeToggle(coordinator, client, config_entry.data))

    _LOGGER.debug("async_setup_entry adding %d entities", len(entities))
    async_add_entities(entities, True)


class JBDChargeToggle(BMSEntity, ToggleEntity):
    """Representation of the charge toggle of a JBD BMS."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        client: JBD,
        config_entry_data: Mapping[str, Any],
    ) -> None:
        """Initialize the toggle."""
        super().__init__(coordinator, config_entry_data)
        self.entity_description = ToggleEntityDescription(
            key=JBDBasicInfoSensor.CHARGING_ENABLED,
            name="Charging",
        )
        self.client = client

    @property
    def is_on(self):
        """Return the toggle value from the lookup table."""
        is_on = self.coordinator.data[COORDINATOR_DATA_BASIC_INFO][
            JBDBasicInfoSensor.CHARGING_ENABLED
        ]
        _LOGGER.debug(f"Charge is {'on' if is_on else 'off'}")
        return is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the charge MOSFET on (i.e. conducting)."""
        # The two toggles can only be set at once, thus we have to set the existing state for the discharge toggle
        discharge_enabled = self.coordinator.data[COORDINATOR_DATA_BASIC_INFO][
            JBDBasicInfoSensor.DISCHARGING_ENABLED
        ]

        _LOGGER.debug("Sending enable charge")
        self.client.chgDsgEnable(True, discharge_enabled)

        attempts = 5
        while (
            not self.client.readBasicInfo()[JBDBasicInfoSensor.CHARGING_ENABLED]
            and attempts > 0
        ):
            _LOGGER.debug("Waiting for charge to be enabled...")
            attempts -= 1

        _LOGGER.debug("Charge enabled!")
        await self.coordinator.async_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the charge MOSFET off (i.e. not conducting)."""
        # The two toggles can only be set at once, thus we have to set the existing state for the discharge toggle
        discharge_enabled = self.coordinator.data[COORDINATOR_DATA_BASIC_INFO][
            JBDBasicInfoSensor.DISCHARGING_ENABLED
        ]

        _LOGGER.debug("Sending disable charge")
        self.client.chgDsgEnable(False, discharge_enabled)

        attempts = 5
        while (
            self.client.readBasicInfo()[JBDBasicInfoSensor.CHARGING_ENABLED]
            and attempts > 0
        ):
            _LOGGER.debug("Waiting for charge to be disabled...")
            attempts -= 1

        _LOGGER.debug("Charge disabled!")
        await self.coordinator.async_refresh()


class JBDDischargeToggle(BMSEntity, ToggleEntity):
    """Representation of the discharge toggle of a JBD BMS."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        client: JBD,
        config_entry_data: Mapping[str, Any],
    ) -> None:
        """Initialize the toggle."""
        super().__init__(coordinator, config_entry_data)
        self.entity_description = ToggleEntityDescription(
            key=JBDBasicInfoSensor.DISCHARGING_ENABLED,
            name="Discharging",
        )
        self.client = client

    @property
    def is_on(self):
        """Return the toggle value from the lookup table."""
        is_on = self.coordinator.data[COORDINATOR_DATA_BASIC_INFO][
            JBDBasicInfoSensor.DISCHARGING_ENABLED
        ]
        _LOGGER.debug(f"Discharge is {'on' if is_on else 'off'}")
        return is_on

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the discharge MOSFET on (i.e. conducting)."""
        # The two toggles can only be set at once, thus we have to set the existing state for the charge toggle
        charge_enabled = self.coordinator.data[COORDINATOR_DATA_BASIC_INFO][
            JBDBasicInfoSensor.CHARGING_ENABLED
        ]

        _LOGGER.debug("Sending enable discharge")
        self.client.chgDsgEnable(charge_enabled, True)

        attempts = 5
        while (
            not self.client.readBasicInfo()[JBDBasicInfoSensor.DISCHARGING_ENABLED]
            and attempts > 0
        ):
            _LOGGER.debug("Waiting for discharge to be enabled...")
            attempts -= 1

        _LOGGER.debug("Discharge enabled!")
        await self.coordinator.async_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the discharge MOSFET off (i.e. not conducting)."""
        # The two toggles can only be set at once, thus we have to set the existing state for the charge toggle
        charge_enabled = self.coordinator.data[COORDINATOR_DATA_BASIC_INFO][
            JBDBasicInfoSensor.CHARGING_ENABLED
        ]

        _LOGGER.debug("Sending disable discharge")
        self.client.chgDsgEnable(charge_enabled, False)

        attempts = 5
        while (
            self.client.readBasicInfo()[JBDBasicInfoSensor.DISCHARGING_ENABLED]
            and attempts > 0
        ):
            _LOGGER.debug("Waiting for discharge to be disabled...")
            attempts -= 1

        _LOGGER.debug("Discharge disabled!")
        await self.coordinator.async_refresh()
