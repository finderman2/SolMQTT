# SolMQTT
A collection of scripts to support data logging from solar charge controllers and inverters.
## Overview
These scripts are designed to output data from various solar power electronics (grid-tie inverters, charge controllers) using the MQTT protocol. This more open format can be logged and tracked in a varity of ways, my current preference is to use the fantastic EmonCMS/emonPi platform in conjuction with NodeRED to do long term data logging.

## Current Supported Hardware
* Midnite Classic 150, 200, 250 (note only tested on 250, but data structure is the same)
* SolarEdge SE5000 inverter (currently untested, designed to communicate over MODBUS/TCP)
* more to come as I get access...

## Dependencies:
* [pyModbusTCP](https://github.com/sourceperl/pyModbusTCP)
* paho-mqtt
