'''
### Schneider Electric Conext MPPT 60-150 MQTT Logger ##
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
mqttclient = mqtt.Client("conextMPPT") #create new instance
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
DEVNAME = "conextMPPT" ## Name used in prefix for MQTT publish
MODBUSID = 30
LIMIT = 30 #amp limit

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

def limitCurrent(current):
    global client
    print("Limiting current to: "+str(current))
    rq = client.write_register(4147, int(current*10))
    assert(rq.function_code < 0x80) 


##Basic Charge Modes and errors states
def ccStatus(status):
    codes = {
            768: "Not Charging",
            769: "Bulk",
            770: "Absorption",
            771: "Overcharge",
            772: "Equalize",
            773: "Float",
            774: "No Float",
            775: "Constant VI",
            776: "Charger Disabled",
            777: "Qualifying AC",
            778: "Qualifying APS",
            779: "Engaging Charger",
            780: "Charge Fault",
            781: "Charger Suspend",
            782: "AC Good",
            783: "APS Good",
            784: "AC Fault",
            785: "Charge",
            786: "Absorption Exit Pending",
            787: "Ground Fault",
            788: "AC Good Pending"
        }
    return codes.get(status, "Invalid status code")

##not finished
def ccFault0(status):
    codes = {
            768: "Capacitor Over-Temperature",
            769: "Battery Over-Temperature",
            770: "Ambient Over-Temperature",
            771: "Overcharge",
            772: "Equalize",
            773: "Float",
            774: "No Float",
            775: "Constant VI",
            776: "Charger Disabled",
            777: "Qualifying AC",
            778: "Qualifying APS",
            779: "Engaging Charger",
            780: "Charge Fault",
            781: "Charger Suspend",
            782: "AC Good",
            783: "APS Good",
            784: "AC Fault",
            785: "Charge",
            786: "Absorption Exit Pending",
            787: "Ground Fault",
            788: "AC Good Pending"
        }
    return codes.get(status, "Invalid fault code")

def readAll():
    global OUTVOLT, OUTCURR, OUTPOWER, INVOLT, INCURR, INPOWER, POWERTDY, CHGRSTAT, BTEMP
    print("Reading...")
    global client
    base = 0x0000
    rq = client.read_holding_registers(base, 120)
    
    if debug > 0:
        print("Register Dump: ") #dump out the whole register
        print(rq)
    
        i=0 # go over each item and print it with it's position
        for item in rq:
            print("Reg"+str(i)+": ", end='')
            print(rq[i])
            i = i+1
    
    if rq != None:
        OUTVOLT = ((rq[0x0059] << 16) + rq[0x0058]) * 0.001 ## data is uint16 LSB, so shift high byte over then add LSB
        OUTCURR = ((rq[0x005b] << 16) + rq[0x005a]) * 0.001
        OUTPOWER = ((rq[0x005d] << 16) + rq[0x005c])

        INVOLT = ((rq[0x004d] << 16) + rq[0x004c]) * 0.001 ## data is uint16 LSB, so shift high byte over then add LSB, then x scale factor
        INCURR = ((rq[0x004f] << 16) + rq[0x004e]) * 0.001
        INPOWER = ((rq[0x0051] << 16) + rq[0x0050])

        BTEMP = (rq[0x0056-base] * 0.01 ) + -273
        POWERTDY = rq[0x6a] * 0.001 ## kwh collected today
        CHGRSTAT = ccStatus(rq[0x49]) ##return charger status string from code
        
    else:
        print("Request failed")

def forcefloat():
    print("Forcing float")
    global client
    rq = client.write_register(0x00aa, 0x02)

def forcebulk():
    print ("Forcing bulk")
    global client
    rq = client.write_register(0x00aa, 0x01)

def monitor():
    readAll()
    print("\nBattery")
    print("Bat Volts: "+str(OUTTVOLT))
    print("Bat Amps: "+str(OUTTCURR))
    print("Bat Power: "+str(OUTPOWER))
    print("\nPV")
    print("PV Volts: "+str(INVOLT))
    print("PV Amps: "+str(INCURR))
    print("PV Power: "+str(INPOWER))
    
    print("\n")
    print("kWh Collected Today"+str(POWERTDY))
    print(CHGRSTAT)
    
def mqttPub():
    readAll()
    print("Publishing to broker...: ")
    
    mqttclient.publish(DEVNAME+"/device/status", CHGRSTAT) #status i.e. bulk, absorb, float
    
    #Output is battery side
    mqttclient.publish(DEVNAME+"/bat/volts", OUTVOLT)
    mqttclient.publish(DEVNAME+"/bat/amps", OUTCURR)
    mqttclient.publish(DEVNAME+"/bat/power", OUTPOWER)
    
    #Input is PV side
    mqttclient.publish(DEVNAME+"/pv/volts", INVOLT)
    mqttclient.publish(DEVNAME+"/pv/amps", INCURR)
    mqttclient.publish(DEVNAME+"/pv/power", INPOWER)
    
    #Accumulators
    mqttclient.publish(DEVNAME+"/bat/kwhtoday", POWERTDY) # energy put into the battery
        
    #Temps
    mqttclient.publish(DEVNAME+"/bat/temp", BTEMP)
    
def main(argv):
    global client		
    global SERIAL1
    global SERIAL2

    if (sys.argv[1] == 'forceeq'): 
        connect()
        forceeq(float(sys.argv[2]), int(sys.argv[3]))
        close()

    if (sys.argv[1] == 'forcefloat'): 
        connect()
        forcefloat()
        close()

    if (sys.argv[1] == 'forcebulk'): 
        connect()
        forcebulk()
        close()

    if (sys.argv[1] == 'limit'): 
        connect()
        limitCurrent(int(sys.argv[2]))
        close()
    
    if (sys.argv[1] == 'finishcharge'): 
        connect()
        limitCurrent(0)
        close()

    if (sys.argv[1] == 'readall'): 
        readAll()	
        
    if (sys.argv[1] == 'monitor'): 
        monitor()		  
    
    if (sys.argv[1] == 'publish'):
        mqttPub()
    
    print("Done.")

t=time.time()

if __name__ == "__main__":
    #main(sys.argv[1:])
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