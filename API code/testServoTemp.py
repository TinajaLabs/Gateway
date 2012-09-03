# testservotemp.py
# read a temp sensor and adjust the servo setting
# this is a test of opening and closing a damper in an hvac duct
# works with 2.0.0 lib from this repo: http://code.google.com/p/python-xbee/ 
# Chris Jefferies, 2012.05.13

import serial
import sys
from xbee import XBee
import binascii
import math, time

SERIALPORT = "COM4"    # the com/serial port the XBee is connected to
BAUDRATE = 9600      # the baud rate we talk to the xbee

serial_port = serial.Serial(SERIALPORT,BAUDRATE)
xbee = XBee(serial_port)
xbeeDest = b'\x00\x18' # Decimal 24, MY=18

print "starting testServoTemp..."

# the main function
def mainloop(idleevent):

	global lastServoSetting, defaultDevice

	response = xbee.wait_read_frame()
	xbeeAddr = int(binascii.hexlify(response['source_addr']),16)

	if (xbeeAddr != 10):  # testing the temp data from radio 10
		return

	xbeeRSSI = "rssi: ", int(binascii.hexlify(response['rssi']),16)

	totalmVolts = 0
	sampleCount = len(response['samples'])
	for i in range(sampleCount):
		totalmVolts += response['samples'][i]['adc-1']

	avgTemp = calctemp(totalmVolts/sampleCount)
	print xbeeAddr, avgTemp, lastServoSetting


	# assuming a heating mode, we want to
	# open a vent when the temp goes low
	if (avgTemp >= 72 and lastServoSetting != 0):
		setpos(12,0)
		lastServoSetting = 0

	# close the vent when the temp goes high
	if (avgTemp <= 69 and lastServoSetting != 180):
		setpos(12,180)
		lastServoSetting = 180

	time.sleep(2)

def setpos(device,angle):

	#Check that things are in range
	minAngle = 0.0
	maxAngle = 180.0
	if angle > maxAngle or angle <minAngle:
		angle = 90
		print "WARNING: Angle range should be between 0 and 180. Setting angle to 90 degrees to be safe..."
		print "moving servo "+str(device)+" to "+str(angle)+" degrees."

	minTarget = 3500
	maxTarget = 7500
	scaledValue = int((angle / ((maxAngle - minAngle) / (maxTarget - minTarget))) + minTarget)

	# print "scaledValue: ", scaledValue
	# print "angle: ", angle

	#Get the lowest 7 bits
	bytelow=scaledValue&127
	#Get the highest 7 bits
	bytehigh=(scaledValue-(scaledValue&127))/128

	# Works - Pololu protocol: 0xAA, device number, 0x04, channel number, target low bits, target high bits
	# cmdString=chr(0xAA)+chr(device)+chr(0x04)+chr(0x00)+chr(bytelow)+chr(bytehigh)

	# Works - Compact protocol: 0x84, channel number, target low bits, target high bits
	cmdString=chr(0x84)+chr(0x00)+chr(bytelow)+chr(bytehigh)

	# print "sending: " + cmdString
	xbee.tx(dest_addr=xbeeDest, data=cmdString)


def calctemp(mVolts):

    voltage = mVolts * 3.3 / 1024       # Convert millivolts to Celcius
    tempC = (voltage - .5) * 100        # Convert millivolts to Celcius

    tempF = math.floor(tempC * 9 / 5 + 32)        # Convert to Fehrenheit

    # Print formated tempurature readings
    # print tempC, "C \t", tempF, "F - ", mVolts, voltage
    return tempF


lastServoSetting = 180
defaultDevice = 12

while True:
    mainloop(None)


