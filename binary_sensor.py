"""Support for BMS Tools binary sensors."""
from __future__ import annotations

import logging
from typing import Any, Mapping

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .device import BMSEntity
from .sensor import JBDBasicInfoSensor
from .const import COORDINATOR_DATA_BASIC_INFO, DOMAIN, HASS_DATA_COORDINATOR

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Binary Sensor platform for BMS Tools."""
    entities: list[BinarySensorEntity] = []

    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        HASS_DATA_COORDINATOR
    ]

    for i in range(
        0, coordinator.data[COORDINATOR_DATA_BASIC_INFO][JBDBasicInfoSensor.CELL_COUNT]
    ):
        entities.append(
            JBDBasicInfoBinarySensor(
                coordinator,
                config_entry.data,
                key=JBDBasicInfoBinarySensor.CELL_BALANCING.format(i),
                device_class=BinarySensorDeviceClass.RUNNING,
                name=f"Cell {i} balancing",
                entitiy_category=EntityCategory.DIAGNOSTIC,
            )
        )

    _LOGGER.debug("async_setup_entry adding %d entities", len(entities))
    async_add_entities(entities, True)


class JBDBasicInfoBinarySensor(BMSEntity, BinarySensorEntity):
    """Representation of multiple binary sensors from a JBD BMS basic info register."""

    CELL_BALANCING = "bal{}"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        config_entry_data: Mapping[str, Any],
        key: str,
        device_class: BinarySensorDeviceClass,
        name: str,
        entitiy_category: EntityCategory | None = None,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, config_entry_data)
        self.entity_description = BinarySensorEntityDescription(
            key=key,
            device_class=device_class,
            entity_category=entitiy_category,
            name=name,
        )

    @property
    def is_on(self):
        """Return the binary sensor value from the lookup table."""
        return self.coordinator.data[COORDINATOR_DATA_BASIC_INFO][
            self.entity_description.key
        ]
