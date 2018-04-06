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
mqttclient = mqtt.Client("classicCC") #create new instance
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
SERIAL1 = 46				# The first part of the serial number
SERIAL2 = 567				# The second part of the serial number
HOST = '192.168.2.37'
CCNAME = "classic250" ## Name used in prefix for MQTT publish
LIMIT = 30 #amp limit

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
	
def unlock(serial1,serial2):
	global client
	rq = client.write_registers(20491, [serial1,serial2])
	assert(rq.function_code < 0x80) 

def limitCurrent(current):
    global client
    print "Limiting current to: "+str(current)
    rq = client.write_register(4147, int(current*10))
    assert(rq.function_code < 0x80) 

def readAll():
    global BATTV, BATTCURR, PVVAVG, PVCURR, KWH, WATT, AH, BTEMP, PCBTEMP, FETTEMP
    print "Reading..."
    global client
    base = 4114
    rq = client.read_holding_registers(base,40)
    print(rq)
    #assert(rq.function_code < 0x80)
    BATTV = rq[4114-base]/10.0
    BATTCURR = rq[4116-base]/10.0
    PVVAVG = rq[4115-base]/10.0
    PVCURR = rq[4120-base]/10.0
    KWH = rq[4117-base]/10.0
    WATT = rq[4118-base] #don't div by 10
    AH = rq[4124-base] #also don't div by 10
    BTEMP = rq[4131-base]/10.0
    FETTEMP = rq[4132-base]/10.0
    PCBTEMP = rq[4133-base]/10.0
    #BTEMP = (rq.registers[4131-base]/10.0)*1.8+32

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
    print("Battery voltage: "+str(BATTV))
#     print("Battery current: "+str(BATTCURR))
#     print("PV voltage: "+str(PVVAVG))
#     print("PV current: "+str(PVCURR))
#     print("kWh today: "+str(KWH))
#     print("Watts: "+str(WATT))
#     print("Ah today: "+str(AH))
#     print("BatSense: "+str(BTEMP))
#     print("FET Temp: "+str(FETTEMP))
#     print("PCB Temp: "+str(PCBTEMP))
#     now = datetime.datetime.utcnow()
    
    #Realtime voltage and current
    mqttclient.publish(CCNAME+"/bat/BattV", BATTV)
    mqttclient.publish(CCNAME+"/bat/BattCurr", BATTCURR)
    mqttclient.publish(CCNAME+"/pv/PVVolts", PVVAVG)
    mqttclient.publish(CCNAME+"/pv/PVCurr", PVCURR)
    
    #Accumulators
    mqttclient.publish(CCNAME+"/bat/kwhtoday", KWH)
    mqttclient.publish(CCNAME+"/bat/watts", WATT)
    mqttclient.publish(CCNAME+"/bat/ah", AH)
    
    #Temps cc stand for charge controller
    mqttclient.publish(CCNAME+"/bat/temp", BTEMP)
    mqttclient.publish(CCNAME+"/cc/fets", FETTEMP)
    mqttclient.publish(CCNAME+"/cc/pcb", PCBTEMP)

def mqttPub():
    readAll()
    print("Publishing to broker...: ")
    #Realtime voltage and current
    mqttclient.publish("classic250/bat/BattV", BATTV)
    mqttclient.publish(CCNAME+"/bat/BattCurr", BATTCURR)
    mqttclient.publish(CCNAME+"/pv/PVVolts", PVVAVG)
    mqttclient.publish(CCNAME+"/pv/PVCurr", PVCURR)
    
    #Accumulators
    mqttclient.publish(CCNAME+"/bat/kwhtoday", KWH)
    mqttclient.publish(CCNAME+"/bat/watts", WATT)
    mqttclient.publish(CCNAME+"/bat/ah", AH)
    
    #Temps cc stand for charge controller
    mqttclient.publish(CCNAME+"/bat/temp", BTEMP)
    mqttclient.publish(CCNAME+"/cc/fets", FETTEMP)
    mqttclient.publish(CCNAME+"/cc/pcb", PCBTEMP)
    
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
    #main(sys.argv[1:])
    while True:
        if time.time()-t > 9:
            mqttPub()
            t=time.time()