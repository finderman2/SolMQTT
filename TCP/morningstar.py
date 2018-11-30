'''
### MorningStar TS-MPPT 600 CC MQTT Logger ##
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
import struct
import logging
import time
import datetime
#from threading import Timer
import threading
import paho.mqtt.client as mqtt #import the client1

## Functions ##
def safeDiv(x,y):
    try:
        return x/y
    except ZeroDivisionError:
        return 0
        
def HalfToFloat(h):
    s = int((h >> 15) & 0x00000001)    # sign
    e = int((h >> 10) & 0x0000001f)    # exponent
    f = int(h & 0x000003ff)            # fraction

    if e == 0:
       if f == 0:
          return int(s << 31)
       else:
          while not (f & 0x00000400):
             f <<= 1
             e -= 1
          e += 1
          f &= ~0x00000400
          #print(s,e,f)
    elif e == 31:
       if f == 0:
          return int((s << 31) | 0x7f800000)
       else:
          return int((s << 31) | 0x7f800000 | (f << 13))

    e = e + (127 -15)
    f = f << 13

    return int((s << 31) | (e << 23) | f)

def FloatFromInt (number):
    x = HalfToFloat(number)
    # hack to coerce int to float
    str = struct.pack('I',x)
    f=struct.unpack('f', str)

    # print the floating point
    return f[0]

#Setup debug logging
logging.basicConfig(filename='morningst-errors.log',level=logging.WARNING)
log = logging.getLogger()
log.setLevel(logging.WARNING) #Debug ON

debug = 0

''' 
### MQTT Settings ###
'''
broker_address="localhost"
mqttclient = mqtt.Client("morningstarMPPT600") #create new instance
mqttclient.username_pw_set("emonpi", password="emonpimqtt2016")

#Try connecting to our broker...
try:
    mqttclient.connect(broker_address, port=1883) #connect to broker
except:
    print("Broker Connection Failed")

''' 
### Device Settings ###
Add your host IP address and device name
'''
HOST = '1.10.1.253'
DEVNAME = "MS-MPPT-600"
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
    global  DCV, DCI, DCW, PVVOLT, PVAMP, PVWATT, VBTAR, HTSINKT, DCWH, CHGSTATE, BATTEMP, STATUS
    print("Reading...")
    global client
    base = 0x0018
    rq = client.read_holding_registers(base, 45)
    if debug > 0:
        print("Register Dump: ") #dump out the whole register
        #print(rq)
    
        i=0 # go over each item and print it with it's position
        for item in rq:
            print("Reg"+str(i)+": ", end='')
            print(rq[i])
            i = i+1
    
    if (rq is not None):
        #Register values are returned as a list
        
        #DC Array values
        DCV = FloatFromInt( rq[0x0019-base] ) # DC volts
        DCI = FloatFromInt( rq[0x001C-base] ) # DC current
        DCW = FloatFromInt( rq[0x003a-base] ) #Output watts
        VBTAR = FloatFromInt( rq[0x0033-base] ) #Current charge target voltage
        PVVOLT = FloatFromInt( rq[0x001b-base] )
        PVAMP = FloatFromInt( rq[0x001d-base] )
        PVWATT = FloatFromInt( rq[0x003b-base] ) 
           
        HTSINKT = FloatFromInt( rq[0x0023-base] )
        BATTEMP = FloatFromInt( rq[0x0024-base] )
        DCWH = FloatFromInt( rq[0x0044-base] )        

        CHGSTATE = rq[0x0032-base] #charge status
        if (CHGSTATE == 0):
            STATUS = "Start"
        elif (CHGSTATE == 1):
            STATUS = "Night Check"
        elif (CHGSTATE == 2):
            STATUS = "Disconnect"
        elif (CHGSTATE == 3):
                STATUS = "Night"
        elif (CHGSTATE == 4):
                STATUS = "Fault"
        elif (CHGSTATE == 5):
                STATUS = "MPPT"
        elif (CHGSTATE == 6):
                STATUS = "Absorption"
        elif (CHGSTATE == 7):
                STATUS = "Float"
        elif (CHGSTATE == 8):
                STATUS = "Equalize"
        elif (CHGSTATE == 9):
                STATUS = "Disconnect"
        elif (CHGSTATE == 10):
                STATUS = "Fixed"
        else:
            STATUS = "Error No State"
    else:
        print("error no data")

def monitor():
    readAll()
    now = datetime.datetime.utcnow()
    print(now)
    print("Charge Status: "+STATUS + "\n")
    
    print("DC Volts: "+str(DCV))
    print("DC current: "+str(DCI))
    print("DC power: "+str(DCW) + "\n")
    print("Vbat Target: "+str(VBTAR) + "\n")    
    print("Battery Temp C: "+str(BATTEMP)+"\n")

    print("PV Volts: "+str(PVVOLT))
    
    print("PV current: "+str(PVAMP))
    print("Output power: "+str(PVWATT) + "\n")
    
    print("Heatsink Temp C: "+str(HTSINKT))

def mqttPub():
    readAll()
    print("Publishing to broker...: ")
    #Realtime voltage and current
    mqttclient.publish(DEVNAME+"/device/status", STATUS)
    
    mqttclient.publish(DEVNAME+"/DC/volts", DCV)
    mqttclient.publish(DEVNAME+"/DC/amps", DCI)
    mqttclient.publish(DEVNAME+"/DC/watts", DCW)
    
    mqttclient.publish(DEVNAME+"/PV/volts", PVVOLT)
    mqttclient.publish(DEVNAME+"/PV/amps", PVAMP)
    mqttclient.publish(DEVNAME+"/PV/watts", PVWATT)
    
    #Accumulators
    mqttclient.publish(DEVNAME+"/dc/dailyWh", DCWH)
    
    #Temps cc stand for charge controller
    mqttclient.publish(DEVNAME+"/temps/heatsink", HTSINKT)
    mqttclient.publish(DEVNAME+"/temps/battery", BATTEMP)       
def main(argv):
    global client

    if (sys.argv[1] == 'readall'): 
        readAll()
        
    if (sys.argv[1] == 'monitor'): 
        monitor()
    if (sys.argv[1] == 'publish'): 
        mqttPub()                 

    print("Done.")

t=time.time()

now = datetime.datetime.utcnow()
logging.warning(str(now))
logging.warning("Program Running")

if __name__ == "__main__":
    #main(sys.argv[1:])
    while True:
         if time.time()-t > 10:
             for i in range(5):
                 try:
                     mqttPub()
                 except TypeError as e:
                     time.sleep(1)
                     continue
                 else:
                     break
             else:
                 now = datetime.datetime.utcnow()
                 logging.warning(str(now))
                 logging.warning("Can't reach device")

             t=time.time()