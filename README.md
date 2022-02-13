# Home Assistant BMS Tools Integration
This integration is based on the BMS Tools project by Eric Poulsen: https://gitlab.com/bms-tools/bms-tools

A config flow is available that allows selecting the serial port of the connected BMS and assigning a serial number to connect multiple BMS.<br>
Bluetooth is not supported (yet) by the underlying library.

Installable via HACS as custom repository ([Guide](https://codingcyclist.medium.com/how-to-install-any-custom-component-from-github-in-less-than-5-minutes-ad84e6dc56ff)).

# Currently supported BMS
- JBD / Overkill Solar

# Features

Sensors:
- Battery voltage
- Battery current
- Battery power
- Battery state of charge (%)
- Cell voltages
- Cell balancing status
- Cycle count
- Temperature

Controls:
- Charging switch
- Discharging switch

## Support for Home Assistant Energy Management
Since this feature needs two separate sensors for charge and discharge, two additional sensors are available:
- Battery charge power
- Battery discharge power

You can then add two Riemann sum integral sensors by adding this to your `configuration.yaml`:
```
sensor:
  - platform: integration
    source: sensor.charge_power
    name: Battery Charged Energy
    unit_prefix: k
    round: 2
  - platform: integration
    source: sensor.discharge_power
    name: Battery Discharged Energy
    unit_prefix: k
    round: 2
```

See https://www.home-assistant.io/integrations/integration/ for more information.
