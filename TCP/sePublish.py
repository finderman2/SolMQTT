'''
### Solaredge Inverter MQTT Logger ##
designed for use with emoncms to log solar energy data

Parts of original code by stephendv (https://github.com/stephendv/IslandManager)
Further additions and fixes by Liam O'Brien

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

#Setup debug logging
logging.basicConfig()
log = logging.getLogger()
#log.setLevel(logging.DEBUG) #Debug ON
debug = 1

''' 
### MQTT Settings ###
'''
broker_address="test.mosquitto.org"
mqttclient = mqtt.Client("classicCC") #create new instance

#Try connecting to our broker...
try:
    mqttclient.connect(broker_address, port=1883) #connect to broker
except:
    print("Broker Connection Failed")

''' 
### Midnite Charge Controller Settings ###
Add your serial number and IP address here
'''
HOST = '192.168.1.22'
CCNAME = "SE5000"
client = ModbusClient(host=HOST, port=502, auto_open=True)

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

def readAll():
    global PHTYP, ACISF, ACITOT, ACIA, ACIB, ACIC, ACVSF, ACVAB, ACVAN, ACVBN, ACW, ACFREQSF, ACFREQ, ACWHLFSF, ACWHLF, DCVSF, DCISF, DCV, DCI, DCW, HTSINKT, STATUSCODE, STATUS
    print("Reading...")
    global client
    base = 40070
    rq = client.read_holding_registers(40069, 40) #start at 69 to get correct readings  
    if debug > 0:
        print("Register Dump: ") #dump out the whole register
        print(rq)
    
        i=0 # go over each item and print it with it's position
        for item in rq:
            print("Reg"+str(i)+": ", end='')
            print(rq[i])
            i = i+1
    
    #Register values are returned as a list
    PHTYP = rq[40070-base] # sunspec DID 101=1ph 102=split ph 103=3ph
    
    #AC inverter values
    ACISF = 0.001 #ac current scale factor
    ACITOT = rq[40072-base] * ACISF #total ac current
    ACIA = rq[40073-base] #AC current leg A
    ACIB = rq[40074-base] #AC current leg B
        
    ACVSF = 0.1 #ac volts scale factor
    ACVAB = rq[40077-base] * ACVSF #ac volts A-B
    ACVAN = rq[40080-base] * ACVSF #ac volts A to nuetral
    ACVBN = rq[40081-base] * ACVSF #ac volts B to nuetral
    ACW   = rq[40085-base] * 0.1
    
    ACFREQSF = 0.001 #ac freq scale factor
    ACFREQ = rq[40086-base] #ac freq
    
    ACWHLFSF = rq[40096-base] #ac lifetime wh production scale factor
    ACWHLF = rq[40094-base] #ac lifetime wh production
    
    #If we have a 3ph system then read out those values
    if (PHTYP == 103):
        ACIC = rq[40075-base] #AC current leg C
    
    #DC Array values
    DCVSF = 0.1 # dc volts scale factor
    DCISF = 0.001 # dc current scale factor
    DCV = rq[40099-base] * DCVSF # DC volts
    DCI = rq[40097-base] * DCISF # DC current
    DCW = rq[40101-base] * 0.1 # DC power
    
    #Temperature values
    HTSINKT = rq[40104-base] * 0.01 #heatsink temp C
    
    STATUSCODE = rq[40108-base] #inverter status 1=Off, 2=Sleeping/Night 4=On/MPPT
    if (STATUSCODE == 1):
        STATUS = "Off"
    elif (STATUSCODE == 2):
        STATUS = "Sleeping/Night"
    elif (STATUSCODE == 4):
        STATUS = "On - MPPT"
    else:
        STATUS = "Error No State"    
    
    # ACVAB = rq[6] * 0.1
#     DCV = rq[28] * 0.1 #NEW dc volts
#     ACW = rq[17] * 0.1 #NEW AC power
#     ACITOT = rq[2] * 0.001 # total AC current reg 1,2
#     ACIT = ACW / ACVAB #AC Current

def monitor():
    readAll()
    now = datetime.datetime.utcnow()
    print(now)
    print("Inverter Status: "+STATUS + "\n")
    
    print("DC Volts: "+str(DCV))
    print("DC current: "+str(DCI))
    print("DC power: "+str(DCW) + "\n")
    
    print("AC Volts: "+str(ACVAB))
    print("AC Volts L1: "+str(ACVAN))
    print("AC Volts L2: "+str(ACVBN))
    
    print("AC current (sum): "+str(ACITOT))
    print("AC power: "+str(ACW) + "\n")
    
    print("Heatsink Temp C: "+str(HTSINKT))

def mqttPub():
    readAll()
    print("Publishing to broker...: ")
    #Realtime voltage and current
    mqttclient.publish(DEVNAME+"/device/status", STATUS)
    
    mqttclient.publish(DEVNAME+"/DC/volts", DCV)
    mqttclient.publish(DEVNAME+"/DC/amps", DCI)
    mqttclient.publish(DEVNAME+"/DC/watts", DCW)
    
    mqttclient.publish(DEVNAME+"/AC/volts", ACVAB)
    mqttclient.publish(DEVNAME+"/AC/L1", ACVAN)
    mqttclient.publish(DEVNAME+"/AC/L2", ACVBN)
    
    mqttclient.publish(DEVNAME+"/AC/totalamps", ACITOT)
    mqttclient.publish(DEVNAME+"/AC/watts", ACW)
    
    #Accumulators
    mqttclient.publish(DEVNAME+"/AC/lifetimeWh", ACWHLF)
    
    #Temps cc stand for charge controller
    mqttclient.publish(DEVNAME+"/temps/heatsink", HTSINKT)
   
def main(argv):
    global client		

    if (sys.argv[1] == 'readall'): 
        readAll()	
        
    if (sys.argv[1] == 'monitor'): 
        monitor()		  

    print("Done.")

#Create a timer to publsh data every 5 seconds    
#t = threading.Timer(5.0, mqttPub)
#t.start()

t=time.time()

if __name__ == "__main__":
    main(sys.argv[1:])
    # while True:
#         if time.time()-t > 5:
#             mqttPub()
#             t=time.time()