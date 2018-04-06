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
# broker_address="test.mosquitto.org"
# mqttclient = mqtt.Client("classicCC") #create new instance
#
# #Try connecting to our broker...
# try:
#     mqttclient.connect(broker_address, port=1883) #connect to broker
# except:
#     print("Broker Connection Failed")

''' 
### Midnite Charge Controller Settings ###
Add your serial number and IP address here
'''
HOST = '192.168.1.20'
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
    global PHTYP, ACISF, ACITOT,ACIA, ACIB, ACIC, ACVSF, ACVAB, ACFREQSF, ACFREQ, ACWHLFSF, ACWHLF, DCVSF, DCV
    print("Reading...")
    global client
    base = 40070
    rq = client.read_holding_registers(base,39)    
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
    ACISF = rq[40076-base] #ac current scale factor
    ACITOT = rq[40072-base] #total ac current
    ACIA = rq[40073-base] #AC current leg A
    ACIB = rq[40074-base] #AC current leg B
        
    ACVSF = rq[40083-base] #ac volts scale factor
    ACVAB = rq[40077-base] #ac volts A-B
    
    ACFREQSF = rq[40087-base] #ac freq scale factor
    ACFREQ = rq[40086-base] #ac freq
    ACWHLFSF = rq[40096-base] #ac lifetime wh production scale factor
    ACWHLF = rq[40094-base] #ac lifetime wh production
    
    #If we have a 3ph system then read out those values
    if (PHTYP == 103):
        ACIC = rq[40075-base] #AC current leg C
    
    #DC Array values
    DCVSF = rq[40099-base] #dc volts scale factor
    DCV = rq[40100-base] * DCVSF #dc volts
    
    

def monitor():
    readAll()
    print("PV voltage: "+str(DCV))
    now = datetime.datetime.utcnow()
    
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