'''
### Schneider Electric Conext SW 4024, 4048 Inverter MQTT Logger ##
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
mqttclient = mqtt.Client("conextSW") #create new instance
mqttclient.username_pw_set("emonpi", password="emonpimqtt2016")

#Try connecting to our broker...
try:
    mqttclient.connect(broker_address, port=1883) #connect to broker
except:
    print("Broker Connection Failed")

''' 
### Midnite Charge Controller Settings ###
Add your serial number and IP address here
'''
HOST = '192.168.1.5'
DEVNAME = "conextSW4048" ## Name used in prefix for MQTT publish
MODBUSID = 91

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
    global LOADAC1VOLT, LOADPOWER, LOADPOWERVA, INVOLT, INCURR, INPOWER, CHGRSTAT, BTEMP, BATKWHTDY
    print "Reading..."
    global client
    base = 0x0040
    rq = client.read_holding_registers(base, 120)
    #print(rq)
    
    #print(rq[0x49])
    #print("end test")
    
    if rq != None:
        #AC Side
        LOADACVOLT = rq[0x0078-base]*0.001
        LOADPOWER = rq[0x0084-base]
        LOADPOWERVA = rq[0x008a-base]
        
        #DC side
        INVOLT = rq[0x004e-base] * 0.001
        INCURR = rq[0x0050-base] * 0.001 #WRONG VALUE, needs to be 2s comp
        INPOWER = rq[0x0052-base] #WRONG VALUE, needs to be 2s comp
        BTEMP = (rq[0x0054-base] * 0.01 ) + -273
        
        #Extras
        BATKWHTDY = rq[0x0094-base] * 0.001
        INVSTAT = invStatus(rq[0x004b-base]) ##return inverter status string from code
        WMAP = wMap(rq[0x004a-base]) ##return inverter warning message from code        
    else:
        LOADAC1VOLT = 0 
        LOADAC2VOLT = 0
        OUTPOWER = 0
        INVOLT = 0
        INCURR = 0
        INPOWER = 0
        print("Request failed")
    
    print("\nOutput")
    print("Inverter Status: "+str(INVSTAT))
    print("Warning Status: "+str(WMAP))
    print("AC Volts: "+ str(LOADACVOLT))
    print("AC Power: "+ str(LOADPOWER))
    print("AC Power Apparent: "+ str(LOADPOWERVA)) #WRONG VALUE returned
    print("\nInput")
    print("Input Volts: " + str(INVOLT))
    print("Input Current: " + str(INCURR))
    print("Input Power: " + str(INPOWER))
    print("Battery Temp: " + str(BTEMP))
    print("Battery kWh Today: " + str(BATKWHTDY))

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
    mqttclient.publish(DEVNAME+"/bat/BattV", INVOLT)
    mqttclient.publish(DEVNAME+"/bat/BattCurr", INCURR)
    
    #Accumulators
    mqttclient.publish(DEVNAME+"/bat/kwhToday", BATKWHTDY)
    mqttclient.publish(DEVNAME+"/bat/watts", INPOWER)
    mqttclient.publish(DEVNAME+"/bat/ah", AH)
    
    #Temps cc stand for charge controller
    mqttclient.publish(DEVNAME+"/bat/temp", BTEMP)
    #mqttclient.publish(DEVNAME+"/cc/fets", FETTEMP)
    #mqttclient.publish(DEVNAME+"/cc/pcb", PCBTEMP)
    
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