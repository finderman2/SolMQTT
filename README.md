# SolMQTT
A collection of scripts to support data logging from solar charge controllers and inverters.
## Overview
These scripts are designed to output data from various solar power electronics (grid-tie inverters, charge controllers) using the MQTT protocol. This more open format can be logged and tracked in a variety of ways, with my current preference being the fantastic EmonCMS/emonPi platform in conjunction with NodeRED to do long term data logging.

## Current Supported Hardware
* Midnite Classic 150, 200, 250 (tested on a 250, but data structure is the same)
* SolarEdge SE5000 inverter (tested with an SE5000, for MODBUS/TCP)
* Schneider Electric Conext series inverter (4024, 4048) and charge controller (MPPT 60-150)
* SunnyBoy SB7000 (not ready for release, RTU/RS485)
* more to come as I get access...

## Dependencies:
* [pyModbusTCP](https://github.com/sourceperl/pyModbusTCP)
* paho-mqtt
