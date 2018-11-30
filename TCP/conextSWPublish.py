'''
### Schneider Electric Conext SW 4024, 4048 Inverter MQTT Logger ##
designed for use with emoncms to log solar energy data

Parts of original code by stephendv (https://github.com/stephendv/IslandManager)

Dependencies:
https://github.com/sourceperl/pyModbusTCP
paho-mqtt
'''

from __future__ import print_function

from pyModbusTCP.client import ModbusClient
import sys
import logging
import time
import datetime
#from threading import Timer
import threading
import paho.mqtt.client as mqtt #import the client1

#Switch MQTT on or off
mqttEnable = 1
#Setup debug logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG) #Debug ON
debug = 0

''' 
### MQTT Settings ###
'''
broker_address="localhost"
mqttclient = mqtt.Client("conextSW") #create new instance
mqttclient.username_pw_set("emonpi", password="emonpimqtt2016")

#Try connecting to our broker...
try:
    mqttclient.connect(broker_address, port=1883) #connect to broker
except:
    print("Broker Connection Failed")

''' 
### Device Settings ###
Add your device name and IP address, and MODBUS ID here
'''
HOST = '192.168.8.170'
DEVNAME = "conextSW4048" ## Name used in prefix for MQTT publish
MODBUSID = 90

client = ModbusClient(host=HOST, port=502, unit_id=MODBUSID, auto_open=True)

def twoComp(number):
    return (0xffff - number) >> 1

def connect():
	global client
	connected = 0 
	count = 0
	while (not connected):
		resp = client.open()
		if (resp == False):
			time.sleep(10)
		else:
			connected = 1 
		count = count + 1

def close():
	global client
	client.close()


def invStatus(status):
    codes = {
            1024: "Invert",
            1025: "AC Pass Through",
            1026: "APS Only",
            1027: "Load Sense",
            1028: "Inverter Disabled",
            1029: "Load Sense Ready",
            1030: "Engaging Inverter",
            1031: "Invert Fault",
            1032: "Inverter Standby",
            1033: "Grid-Tied",
            1034: "Grid Support",
            1035: "Gen Support",
            1036: "Sell-to-Grid",
            1037: "Load Shaving",
            1038: "Grid Frequency Stabilization"
        }
    return codes.get(status, "Invalid status code")

#Fault Bitmap 2
def fMap2(status):
    codes = {
            0: "Reserved",
            1: "Battery Sensor Short",
            2: "Power Board Over-Temper",
            3: "Dead Battery Detected",
            4: "Multi-Unit Frequency Error",
            5: "MPPT Ground Fault",
            6: "Wrong Battery Temperature Sensor"
        }
    return codes.get(status, "Invalid error code")
    
##Warning Bitmap
def wMap(status):
    codes = {
            0: "No Warnings",
            1: "DC Under Voltage",
            2: "AGS Not Connected",
        }
    return codes.get(status, "Invalid warning code")

def readAll():
    global INVSTAT, WMAP, LOADACVOLT, LOADACCURR, LOADACPOWER, LOADPOWERVA, LOADACFREQ, BATTVOLTS, BATTCURR, BATTWATTS, INVPOWER, CHGRSTAT, BTEMP, BATKWHTDY
    print("Reading...")
    global client
    base = 0x0040
    rq = client.read_holding_registers(base, 122)
    if debug > 0:
        print("Register Dump: ") #dump out the whole register
        print(rq)
    
        i=0 # go over each item and print it with it's position
        for item in rq:
            print("Reg"+str(i)+": ", end='')
            print(rq[i])
            i = i+1
    
    if (rq is not None):
        #AC Side
	LOADACVOLT = ((rq[0x0079-base] << 16) + rq[0x0078-base]) * 0.001
        LOADACCURR = ((rq[0x0083-base] << 16) + rq[0x0082-base]) * 0.001
	LOADACPOWER = ((rq[0x0085-base] << 16) + rq[0x0084-base])
        LOADPOWERVA = ((rq[0x0089-base] << 16) + rq[0x0088-base])
	LOADACFREQ = rq[0x008a-base] * 0.01	
        
        #DC side
        BATTVOLTS = ((rq[0x004f-base] << 16) + rq[0x004e-base]) * 0.001
        BATTCURR = ((rq[0x0051-base] << 16) + rq[0x0050-base]) * 0.001 # needs to be 2s comp
        BATTWATTS = ((rq[0x0059-base] << 16) + rq[0x0058-base])
        BTEMP = (rq[0x0054-base] * 0.01 ) + -273
        
        INVPOWER = rq[0x0058-base]
        
        #Extras
        BATKWHTDY = rq[0x0094-base] * 0.001
        INVSTAT = invStatus(rq[0x004b-base]) ##return inverter status string from code
        WMAP = wMap(rq[0x004a-base]) ##return inverter warning message from code        
    else:
        print("Request failed")

def monitor():
    readAll()
    print("\nOutput")
    print("Inverter Status: "+str(INVSTAT))
    print("Warning Status: "+str(WMAP)+"\n")
    print("AC Volts: "+ str(LOADACVOLT))
    print("AC Current: "+ str(LOADACCURR))
    print("AC Freq: "+ str(LOADACFREQ))
    print("AC Power: "+ str(LOADPOWER))
    print("AC Power Apparent: "+ str(LOADPOWERVA)) #WRONG VALUE returned
    print("\nInput")
    print("Input Volts: " + str(BATTVOLTS))
    print("Input Current: " + str(BATTCURR))
    print("Input Power: " + str(BATTWATTS))
    print("Invert Power: " + str(INVPOWER))
    print("Battery Temp: " + str(BTEMP))
    print("Battery kWh Today: " + str(BATKWHTDY))

def mqttPub():
    readAll()
    print("Publishing to broker...: ")
    
    mqttclient.publish(DEVNAME+"/device/status", INVSTAT)
    mqttclient.publish(DEVNAME+"/device/warnings", WMAP)
    
    mqttclient.publish(DEVNAME+"/dc/volts", BATTVOLTS)
    ##mqttclient.publish(DEVNAME+"/dc/amps", BATTCURR)
    mqttclient.publish(DEVNAME+"/dc/power", BATTWATTS)
    
    mqttclient.publish(DEVNAME+"/ac/volts", LOADACVOLT)
    mqttclient.publish(DEVNAME+"/ac/amps", LOADACCURR)
    mqttclient.publish(DEVNAME+"/ac/power", LOADACPOWER)
    mqttclient.publish(DEVNAME+"/ac/freq", LOADACFREQ)
    mqttclient.publish(DEVNAME+"/ac/VA", LOADPOWERVA)
    
    mqttclient.publish(DEVNAME+"/bat/kwhToday", BATKWHTDY) # energy taken from battery
    
    mqttclient.publish(DEVNAME+"/bat/temp", BTEMP)
    
def main(argv):
    global client		
    global SERIAL1
    global SERIAL2

    if (sys.argv[1] == 'readall'): 
        readAll()	
        
    if (sys.argv[1] == 'monitor'): 
        monitor()		  
    if (sys.argv[1] == 'publish'):
        mqttPub()
    print("Done.")

t=time.time()

if __name__ == "__main__":
    while True:
        if time.time()-t > 10:
            for i in range(5):
                try:
                    mqttPub()
                except TypeError as e:
                    now = datetime.datetime.utcnow()
                    logging.warning(str(now))
                    logging.warning("Couldn't reach device, sleeping for 1s")

                    time.sleep(1)
                    continue
                else:
                    break
            else:
                now = datetime.datetime.utcnow()
                logging.warning(str(now))
                logging.warning("Tried 5 times, can't reach device")

            t=time.time()