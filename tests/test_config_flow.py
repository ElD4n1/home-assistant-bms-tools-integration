import pytest
from unittest.mock import patch, MagicMock

from homeassistant import config_entries, data_entry_flow
from homeassistant.const import CONF_PORT

from custom_components.bmstools.config_flow import BMSToolsConfigFlow, connect_and_read_device_info
from custom_components.bmstools.const import DOMAIN, ATTR_SERIAL_NUMBER

@pytest.fixture
def mock_bms_tools():
    with patch("custom_components.bmstools.config_flow.connect_and_read_device_info", return_value={"serial_number": "123456"}):
        yield

@pytest.fixture
def mock_serial_tools():
    with patch("custom_components.bmstools.config_flow.scan_comports", return_value=(["COM1", "COM2"], "COM1")):
        yield

async def test_async_step_user(hass, mock_bms_tools, mock_serial_tools):
    """Test the async_step_user method."""
    flow = BMSToolsConfigFlow()
    flow.hass = hass

    result = await flow.async_step_user(user_input=None)
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "init"

async def test_async_step_init(hass, mock_bms_tools, mock_serial_tools):
    """Test the async_step_init method."""
    flow = BMSToolsConfigFlow()
    flow.hass = hass

    result = await flow.async_step_init(user_input=None)
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "init"

    result = await flow.async_step_init(user_input={CONF_PORT: "COM1"})
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["title"] == "BMS Tools"
    assert result["data"] == {CONF_PORT: "COM1", ATTR_SERIAL_NUMBER: "123456"}

async def test_async_step_serial_number(hass, mock_bms_tools):
    """Test the async_step_serial_number method."""
    flow = BMSToolsConfigFlow()
    flow.hass = hass
    flow.init_info = {CONF_PORT: "COM1", ATTR_SERIAL_NUMBER: 0}

    result = await flow.async_step_serial_number(user_input=None)
    assert result["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result["step_id"] == "serial_number"

    result = await flow.async_step_serial_number(user_input={"consent": True})
    assert result["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY
    assert result["title"] == "BMS Tools"
    assert result["data"] == {CONF_PORT: "COM1", ATTR_SERIAL_NUMBER: 1}
