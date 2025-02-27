"""Support for BMS Tools' supported Battery Management Systems."""
from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    PERCENTAGE,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .device import BMSEntity
from .const import (
    COORDINATOR_DATA_BASIC_INFO,
    COORDINATOR_DATA_CELL_INFO,
    DOMAIN,
    HASS_DATA_COORDINATOR,
)

_LOGGER = logging.getLogger(__name__)

# TODO make polling interval configurable (or is it configurable by default?)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up BMS sensor based on a config entry."""
    entities: list[SensorEntity] = []

    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id][
        HASS_DATA_COORDINATOR
    ]
    data = config_entry.data

    entities.append(
        JBDBasicInfoSensor(
            coordinator,
            data,
            key=JBDBasicInfoSensor.BATTERY_SOC_PERCENT,
            device_class=SensorDeviceClass.BATTERY,
            native_unit_of_measurement=PERCENTAGE,
            name="SoC",
        )
    )
    entities.append(
        JBDBasicInfoSensor(
            coordinator,
            data,
            key=JBDBasicInfoSensor.BATTERY_VOLTAGE,
            device_class=SensorDeviceClass.VOLTAGE,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            name="Voltage",
            divisor=1000,
        )
    )
    entities.append(
        JBDBasicInfoSensor(
            coordinator,
            data,
            key=JBDBasicInfoSensor.BATTERY_CURRENT,
            device_class=SensorDeviceClass.CURRENT,
            native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
            name="Current",
            divisor=1000,
        )
    )
    entities.append(JBDCalculatedPowerSensor(coordinator, data))
    entities.append(JBDCalculatedDischargePowerSensor(coordinator, data))
    entities.append(JBDCalculatedChargePowerSensor(coordinator, data))
    entities.append(
        JBDBasicInfoSensor(
            coordinator,
            data,
            key=JBDBasicInfoSensor.CYCLE_COUNT,
            device_class=None,
            native_unit_of_measurement=None,
            name="Cycle count",
            entitiy_category=EntityCategory.DIAGNOSTIC,
        )
    )
    for i in range(
        0,
        coordinator.data[COORDINATOR_DATA_BASIC_INFO][
            JBDBasicInfoSensor.TEMP_SENSOR_COUNT
        ],
    ):
        entities.append(
            JBDBasicInfoSensor(
                coordinator,
                data,
                key=JBDBasicInfoSensor.TEMPERATURE.format(i),
                device_class=SensorDeviceClass.TEMPERATURE,
                native_unit_of_measurement=UnitOfTemperature.CELSIUS,
                name=f"Temperature {i}",
                entitiy_category=EntityCategory.DIAGNOSTIC,
            )
        )
    for i in range(
        0, coordinator.data[COORDINATOR_DATA_BASIC_INFO][JBDBasicInfoSensor.CELL_COUNT]
    ):
        entities.append(JBDCellVoltageSensor(coordinator, data, i))

    _LOGGER.debug("async_setup_entry adding %d entities", len(entities))
    async_add_entities(entities, True)


# TODO create error enum from error register and display somehow (e.g. simply a translated string)
class JBDBasicInfoSensor(BMSEntity, SensorEntity):
    """Representation of multiple sensors on a JBD BMS from the basic info register."""

    # Constant
    FIRMWARE_VERSION = "version"
    BATTERY_CAPACITY = "full_cap"
    CELL_COUNT = "cell_cnt"
    TEMP_SENSOR_COUNT = "ntc_cnt"
    # Variable
    TEMPERATURE = "ntc{}"
    CYCLE_COUNT = "cycle_cnt"
    BATTERY_SOC_MAH = "cur_cap"
    BATTERY_SOC_PERCENT = "cap_pct"
    BATTERY_VOLTAGE = "pack_mv"
    BATTERY_CURRENT = "pack_ma"
    CHARGING_ENABLED = "chg_fet_en"
    DISCHARGING_ENABLED = "dsg_fet_en"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        config_entry_data: Mapping[str, Any],
        key: str,
        device_class: SensorDeviceClass | None,
        native_unit_of_measurement: str | None,
        name: str,
        state_class: str = SensorStateClass.MEASUREMENT,
        entitiy_category: EntityCategory | None = None,
        divisor: int = 1,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry_data)
        self.entity_description = SensorEntityDescription(
            key=key,
            device_class=device_class,
            native_unit_of_measurement=native_unit_of_measurement,
            state_class=state_class,
            entity_category=entitiy_category,
            name=name,
        )
        self.divisor: int = divisor

    @property
    def native_value(self):
        """Return the sensor value from the lookup table."""
        value = self.coordinator.data[COORDINATOR_DATA_BASIC_INFO][
            self.entity_description.key
        ]
        return value if self.divisor == 1 else round(value / self.divisor, 2)


class JBDCalculatedPowerSensor(BMSEntity, SensorEntity):
    """Representation of a power sensor that is calculated from voltage and current measurements."""

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        config_entry_data: Mapping[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry_data)
        self.entity_description = SensorEntityDescription(
            key="battery_power",
            device_class=SensorDeviceClass.POWER,
            native_unit_of_measurement=UnitOfPower.WATT,
            state_class=SensorStateClass.MEASUREMENT,
            name="Power",
        )

    @property
    def native_value(self):
        """Calculate the sensor value from other values in the lookup table."""
        battery_voltage_mv = self.coordinator.data[COORDINATOR_DATA_BASIC_INFO][
            JBDBasicInfoSensor.BATTERY_VOLTAGE
        ]
        battery_current_ma = self.coordinator.data[COORDINATOR_DATA_BASIC_INFO][
            JBDBasicInfoSensor.BATTERY_CURRENT
        ]
        return (battery_voltage_mv / 1000) * (battery_current_ma / 1000)


class JBDCalculatedDischargePowerSensor(BMSEntity, SensorEntity):
    """
    Representation of a discharge power sensor that is calculated from voltage and current measurements.

    It is set to 0W when the battery is charged and is only needed for integrating the battery into HA Energy Management via a Riemann sum integral.
    """

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        config_entry_data: Mapping[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry_data)
        self.entity_description = SensorEntityDescription(
            key="discharge_power",
            device_class=SensorDeviceClass.POWER,
            native_unit_of_measurement=UnitOfPower.WATT,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            name="Discharge Power",
        )

    @property
    def native_value(self):
        """Calculate the sensor value from other values in the lookup table."""
        battery_voltage_mv = self.coordinator.data[COORDINATOR_DATA_BASIC_INFO][
            JBDBasicInfoSensor.BATTERY_VOLTAGE
        ]
        battery_current_ma = self.coordinator.data[COORDINATOR_DATA_BASIC_INFO][
            JBDBasicInfoSensor.BATTERY_CURRENT
        ]
        battery_power_watts  = (battery_voltage_mv / 1000) * (battery_current_ma / 1000)
        return -battery_power_watts  if battery_power_watts  < 0 else 0


class JBDCalculatedChargePowerSensor(BMSEntity, SensorEntity):
    """
    Representation of a charge power sensor that is calculated from voltage and current measurements.

    It is set to 0W when the battery is disharged and is only needed for integrating the battery into HA Energy Management via a Riemann sum integral.
    """

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        config_entry_data: Mapping[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry_data)
        self.entity_description = SensorEntityDescription(
            key="charge_power",
            device_class=SensorDeviceClass.POWER,
            native_unit_of_measurement=UnitOfPower.WATT,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            name="Charge Power",
        )

    @property
    def native_value(self):
        """Calculate the sensor value from other values in the lookup table."""
        battery_voltage_mv = self.coordinator.data[COORDINATOR_DATA_BASIC_INFO][
            JBDBasicInfoSensor.BATTERY_VOLTAGE
        ]
        battery_current_ma = self.coordinator.data[COORDINATOR_DATA_BASIC_INFO][
            JBDBasicInfoSensor.BATTERY_CURRENT
        ]
        battery_power_watts = (battery_voltage_mv / 1000) * (battery_current_ma / 1000)
        return battery_power_watts if battery_power_watts > 0 else 0


class JBDCellVoltageSensor(BMSEntity, SensorEntity):
    """Representation of multiple sensors on a JBD BMS from the cell info register."""

    CELL_VOLTAGE = "cell{}_mv"

    def __init__(
        self,
        coordinator: DataUpdateCoordinator,
        config_entry_data: Mapping[str, Any],
        cell_number: int,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, config_entry_data)
        self.entity_description = SensorEntityDescription(
            key=JBDCellVoltageSensor.CELL_VOLTAGE.format(cell_number),
            device_class=SensorDeviceClass.VOLTAGE,
            native_unit_of_measurement=UnitOfElectricPotential.VOLT,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
            name=f"Cell {cell_number} voltage",
        )

    @property
    def native_value(self):
        """Return the sensor value from the lookup table."""
        cell_mv = self.coordinator.data[COORDINATOR_DATA_CELL_INFO][
            self.entity_description.key
        ]
        return round(cell_mv / 1000, 3)
