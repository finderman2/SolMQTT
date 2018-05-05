'''
### Schneider Electric Conext MPPT 60-150 MQTT Logger ##
designed for use with emoncms to log solar energy data

Parts of original code by stephendv (https://github.com/stephendv/IslandManager)

Dependencies:
https://github.com/sourceperl/pyModbusTCP
paho-mqtt
'''

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
### Conext Charge Controller Settings ###
Add your the IP address and MODBUS address here
'''
HOST = '192.168.1.5'
DEVNAME = "conextMPPT" ## Name used in prefix for MQTT publish
MODBUSID = 30
LIMIT = 30 #amp limit

client = ModbusClient(host=HOST, port=502, unit_id=MODBUSID, auto_open=True)

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
    print "Limiting current to: "+str(current)
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
    global OUTTVOLT, OUTTCURR, OUTPOWER, INVOLT, INCURR, INPOWER, POWERTDY, CHGRSTAT
    print "Reading..."
    global client
    base = 0x0000
    rq = client.read_holding_registers(base, 120)
    #print(rq)
    
    #print(rq[0x49])
    #print("end test")
    
    if rq != None:
        OUTTVOLT = rq[0x58]*0.001
        OUTTCURR = rq[0x5a]*0.001
        OUTPOWER = rq[0x50]

        INVOLT = rq[0x004c]
        INCURR = rq[0x4e] * 0.001
        INPOWER = rq[0x50]
        POWERTDY = rq[0x6a] * 0.001 ## kwh collected today
        CHGRSTAT = ccStatus(rq[0x49]) ##return charger status string from code
        
    else:
        print("Request failed")
    
    print("\nOutput")
    print(OUTTVOLT)
    print(OUTTCURR)
    print(OUTPOWER)
    print("\nInput")
    print(INVOLT)
    print(INCURR)
    print(INPOWER)
    
    print("\n")
    print(POWERTDY)
    print(CHGRSTAT)
    ##BATTV = rq[0x004e-base]/10.0

def forcefloat():
    print "Forcing float"
    global client
    rq = client.write_register(4159,0x20)
    assert(rq.function_code < 0x80) 

def forcebulk():
    print "Forcing bulk"
    global client
    rq = client.write_register(4159,0x40)
    assert(rq.function_code < 0x80) 

def monitor():
    readAll()
    ##print("Battery voltage: "+str(BATTV))

def mqttPub():
    readAll()
    print("Publishing to broker...: ")
    #Realtime voltage and current
    mqttclient.publish(DEVNAME+"/bat/BattV", BATTV)
    mqttclient.publish(DEVNAME+"/bat/BattCurr", BATTCURR)
    mqttclient.publish(DEVNAME+"/pv/PVVolts", PVVAVG)
    mqttclient.publish(DEVNAME+"/pv/PVCurr", PVCURR)
    
    #Accumulators
    mqttclient.publish(DEVNAME+"/bat/kwhtoday", KWH)
    mqttclient.publish(DEVNAME+"/bat/watts", WATT)
    mqttclient.publish(DEVNAME+"/bat/ah", AH)
    
    #Temps cc stand for charge controller
    mqttclient.publish(DEVNAME+"/bat/temp", BTEMP)
    mqttclient.publish(DEVNAME+"/cc/fets", FETTEMP)
    mqttclient.publish(DEVNAME+"/cc/pcb", PCBTEMP)
    
def main(argv):
    global client		
    global SERIAL1
    global SERIAL2

    if (sys.argv[1] == 'forceeq'): 
        connect()
        unlock(SERIAL1, SERIAL2)
        forceeq(float(sys.argv[2]), int(sys.argv[3]))
        close()

    if (sys.argv[1] == 'forcefloat'): 
        connect()
        unlock(SERIAL1, SERIAL2)
        forcefloat()
        close()

    if (sys.argv[1] == 'forcebulk'): 
        connect()
        unlock(SERIAL1, SERIAL2)
        forcebulk()
        close()

    if (sys.argv[1] == 'limit'): 
        connect()
        unlock(SERIAL1, SERIAL2)
        limitCurrent(int(sys.argv[2]))
        close()
    
    if (sys.argv[1] == 'finishcharge'): 
        connect()
        unlock(SERIAL1, SERIAL2)
        limitCurrent(0)
        close()

    if (sys.argv[1] == 'readall'): 
        readAll()	
        
    if (sys.argv[1] == 'monitor'): 
        monitor()		  

    print "Done."

#Create a timer to publsh data every 5 seconds    
#t = threading.Timer(5.0, mqttPub)
#t.start()

t=time.time()

if __name__ == "__main__":
    main(sys.argv[1:])
    # while True:
#         if time.time()-t > 9:
#             mqttPub()
#             t=time.time()