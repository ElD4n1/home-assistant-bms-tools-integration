import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import async_get_registry
from homeassistant.helpers.entity_registry import async_get_registry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from custom_components.bmstools.device import BMSEntity
from custom_components.bmstools.const import DOMAIN, ATTR_SERIAL_NUMBER, ATTR_MODEL, ATTR_SW_VERSION, ATTR_HW_VERSION

@pytest.fixture
async def device_info_fixture(hass: HomeAssistant):
    """Fixture to set up a Home Assistant instance with a mock BMS Tools integration."""
    config_entry_data = {
        ATTR_SERIAL_NUMBER: "123456",
        ATTR_MODEL: "Test Model",
        ATTR_SW_VERSION: "1.0.0",
        ATTR_HW_VERSION: "1.0.0",
    }
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="BMS Tools",
        update_method=lambda: {},
        update_interval=timedelta(seconds=3),
    )
    await coordinator.async_config_entry_first_refresh()
    entity = BMSEntity(coordinator, config_entry_data)
    return entity

async def test_device_info(hass: HomeAssistant, device_info_fixture):
    """Test the device_info method of BMSEntity."""
    entity = device_info_fixture
    device_info = entity.device_info

    assert device_info[ATTR_IDENTIFIERS] == {(DOMAIN, "123456")}
    assert device_info[ATTR_MANUFACTURER] == "JBD"
    assert device_info[ATTR_MODEL] == "Test Model"
    assert device_info[ATTR_SW_VERSION] == "1.0.0"
    assert device_info[ATTR_HW_VERSION] == "1.0.0"
    assert device_info[ATTR_DEFAULT_NAME] == "Battery Management System"
