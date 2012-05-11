#!/usr/bin/env python
print "Tinaja Labs Sensor Manager..."
print "Tinaja Labs, May 23, 2012 - config updates"
print "--------------------------------------------"

import serial, time, datetime, sys, random, math
import syslog
from xbee import xbee
import sensorhistory

# CJ, 03.12.2011, added these to send feeds to Sen.se
import urllib, urllib2, httplib
import simplejson
print "imported simplejson lib..."

from suds.client import Client
print "imported suds client lib..."

# import twitter
# print "imported twitter lib..."

# For Pachube
import eeml
print "imported eeml lib..."

from xml.etree.ElementTree import ElementTree
print "imported ElementTree for xml configs..."

# set up the base config element
thisTree = ElementTree()
thisTree.parse("tinajaconfig.xml")
tinajaRoot = thisTree.getroot()

############################################### Load Settings
#Get the root node and the devices list
settingslist = tinajaRoot.find('./settings')
serialSetting = getSetting(settingslist, "serial")
print serialSetting.get('id'), serialSetting.get('baudrate'), serialSetting.get('port')
SERIALPORT = serialSetting.get('port')    # the com/serial port the XBee is connected to
BAUDRATE = serialSetting.get('baudrate')     # the baud rate we talk to the xbee

powerSetting = getSetting(settingslist, "power")
print powerSetting.get('id'), powerSetting.get('currentnorm'), powerSetting.get('currentsense'), powerSetting.get('mainvpp'),powerSetting.get('voltsense')
CURRENTSENSE = powerSetting.get('currentsense') # which XBee ADC has current draw data
VOLTSENSE = powerSetting.get('voltsense')       # which XBee ADC has mains voltage data
MAINSVPP = powerSetting.get('mainvpp')          # +-170V is what 120Vrms ends up being (= 120*2sqrt(2))
CURRENTNORM = powerSetting.get('currentnorm')   # conversion to amperes from ADC
vrefcalibration = [0, 
                   488,
                   0,
                   487,
                   485,
                   0,
                   0,
                   0,
                   0,
                   0,
                   0,
                   0,
                   486]

############################################### Load Services
serviceslist = tinajaRoot.find('./services')

webService = getService(serviceslist, "tinajalabs")
TINAJALOGURL = webService.get('url')
logwsdl = TINAJALOGURL + "?wsdl"

webService = getService(serviceslist, "pachube")
PACHUBE_KEY = webService.get('url')

webService = getService(serviceslist, "opensence")
SENSEURL = webService.get('url')
SENSE_KEY = webService.get('apikey')

webService = getService(serviceslist, "opensence")
SENSEURL = webService.get('url')
THINGSPEAK_KEY = webService.get('apikey')

webService = getService(serviceslist, "twitter")
twitterusername = webService.get('uname')
twitterpassword = webService.get('passw')


# open up serial port to collect data received by the xbee
try:
    ser = serial.Serial(SERIALPORT, BAUDRATE)
    ser.open()
    print "TLSM - serial port opened..."
    syslog.syslog("TLSM.opening: serial port opened...")
except Exception, e:
    print "Serial port exception: "+str(e)
    syslog.syslog("TLSM.opening exception: serial port: "+str(e))
    exit

# detect command line arguments
DEBUG = False
if (sys.argv and len(sys.argv) > 1):
    if sys.argv[1] == "-d":
        DEBUG = True

# set up twitter timer
twittertimer = time.time()
twittertimer = 0

# Get the devices list
deviceslist = tinajaRoot.find('./devices')


##############################################################
##############################################################
##############################################################
# the main function
def mainloop(idleevent):
    global sensorhistories, twittertimer, DEBUG, PACHUBE_KEY
    # grab one packet from the xbee, or timeout


    try:
        packet = xbee.find_packet(ser)
        if not packet:
            # print "    no serial packet found... "+ time.strftime("%Y %m %d, %H:%M")
            # syslog.syslog("TLSM.mainloop exception: no serial packet found..." )
            return
    except Exception, e:
        print "TLSM.mainloop exception: Serial packet: "+str(e)
        syslog.syslog("TLSM.mainloop exception: Serial packet: "+str(e))
        return


    try:
        xb = xbee(packet)    # parse the packet
        if not xb:
            print "    no xb packet found..."
            syslog.syslog("TLSM.mainloop exception: no xb packet found...")
            return
    except Exception, e:
        print "TLSM.mainloop exception: xb packet: "+str(e)
        syslog.syslog("TLSM.mainloop exception: xb packet: "+str(e))
        return


    # this traps an error when there is no address_16 attribute for xb
    # why this happens is a mystery to me
    try:
        if xb.address_16 == 99:
            return
    except Exception, e:
        print "xb attribute (address_16) exception: "+str(e)
        syslog.syslog("TLSM.mainloop exception: xb attribute: "+str(e))
        return

    # print xb.address_16, " - ", time.strftime("%Y %m %d, %H:%M"), "rssi:", xb.rssi
    # syslog.syslog(str(xb.address_16) +" - "+ time.strftime("%Y %m %d, %H:%M") + ",  rssi: "+ str(xb.rssi))


    # ------------------------------------------------------------------
    # break out and do something for each device
    try:
        thisDevice = getDevice(deviceslist, str(xb.address_16))
        if thisDevice != None:
            print "This device found: ", thisDevice.get('id'), thisDevice.get('desc')
            print "== Device settings:"
            datafeedslist = thisDevice.find('./datafeeds')
            if datafeedslist != None:
                for datafeed in datafeedslist:
                    print "Device data feeds: ", datafeed.attrib.get("service"), datafeed.attrib.get("id")
        else:
            msg = "This device, "+xb.address_16 + ", was not found in the configuration..."
            print msg
            syslog.syslog("TLSM.mainloop config exception: xb attribute: "+msg
    except Exception, e:
        print "allsensors.mainloop exception: device process "+str(e)


    if xb.address_16 == 99: # Multi-Sensor
        tLogApiKey = ""
        SenseFeedKeys = [0,0,0,0]
        PachubeLogKey = "24660"
        ThingSpeakKey = "604"

        adcinputs = [0,1,2,3]
        for i in range(len(adcinputs)):
            cXbeeAddr = str(xb.address_16)
            cXbeeAdc = str(adcinputs[i])
            adcSensorNum = int(cXbeeAddr + cXbeeAdc)
            avgunit = getmVolts(xb,adcinputs[i])
            if adcinputs[i] == 1:
                avgunit = calctemp(xb)

            SenseFeedKey = str(SenseFeedKeys[i])

            # print "adcSensorNum", adcSensorNum, avgunit
            sensorhistory = sensorhistories.find(adcSensorNum)
            addunithistory(sensorhistory, avgunit)
            fiveminutelog(sensorhistory, tLogApiKey, PachubeLogKey, SenseFeedKey, ThingSpeakKey, 1023, xb.rssi, adcinputs[i])

    else:
        return

        
##############################################################
##############################################################
##############################################################

# sub-routines 
##############################################################
def twitterwatts(lapseMins, twittertimer, loXB):
    # We're going to twitter at midnight, 8am and 4pm
    # Determine the hour of the day (ie 6:42 -> '6')
    currhour = datetime.datetime.now().hour

    # twitter every 8 hours
    # if (((time.time() - twittertimer) >= 3660.0) and (currhour % 8 == 0)):

    return time.time()

    if (((time.time() - twittertimer) >= 3660.0) and (currhour % 8 == 0)):
        print "twittertime!!!"
        twittertimer = time.time();

        if not LOGFILENAME:
            message = appengineauth.gettweetreport()
        else:
            # sum up all the sensors' data
            wattsused = 0
            whused = 0
            for history in sensorhistories.sensorhistories:
                wattsused += history.avgwattover5min()
                whused += history.dayswatthr

            message = "Sensor "+str(loXB.address_16)+" is reporting "+str(int(wattsused))+" Watts, #tweetawatt"

        # write something ourselves
        if message:
            print message, " - time to twitterit..."
            twitterit(twitterusername, twitterpassword, message)

        return ttimer


##############################################################
def fiveminutelog(loSensorHistory, LogApiKey, PachubeLogKey, SenseLogKey, cThingSpeakKey, lnPachubeMaxVal, xbRssi, adcinput):
    # Determine the minute of the hour (ie 6:42 -> '42')
    # currminute = (int(time.time())/60) % 10
    currminute = (int(time.time())/60) % 5
    fiveminutetimer = loSensorHistory.fiveminutetimer

    # Figure out if its been five minutes since our last save
    if (((time.time() - fiveminutetimer) >= 60.0) and (currminute % 5 == 0)):
        # print " . 5min test: time.time()=", time.time(), " fiveminutetimer=", fiveminutetimer, "currminute=", currminute, " currminute % 5: ", currminute % 5                  
        # units used in last 5 minutes
        sensornum = loSensorHistory.sensornum
        avgunitsused = loSensorHistory.avgunitsover5min()

        # print "\n" 
        # print "TLSM.fiveminutelog: " + time.strftime("%Y %m %d, %H:%M")+":  Sensor# "+str(sensornum)+" has averaged: "+str(avgunitsused)
        syslog.syslog("TLSM.fiveminutelog: Sensor# "+str(sensornum)+" has averaged: "+str(avgunitsused))

        lnStartLogging = time.time()
        # log to the local CSV file
        logtocsv(sensornum, avgunitsused, logfile)
        print "  #",sensornum,"time to CSV =", time.time() - lnStartLogging

        lnStartLogging = time.time()
        # send to the tinaja data logger
        # logtotinaja(sensornum, avgunitsused, LogApiKey)
        print "  #",sensornum,"time to TDL =", time.time() - lnStartLogging

        lnStartLogging = time.time()
        # send to the pachube data logger
        logtopachube(sensornum, avgunitsused, PachubeLogKey, lnPachubeMaxVal, xbRssi, adcinput)
        print "  #",sensornum,"time to PDL =", time.time() - lnStartLogging

        # CJ, 03.12.2011, added logtosense() to send feeds to Sen.se
        lnStartLogging = time.time()
        # send to the sen.se data logger
        logtosense(sensornum, avgunitsused, SenseLogKey)
        print "  #",sensornum,"time to SDL =", time.time() - lnStartLogging

       # CJ, 05.04.2011, added logtothing() to send feeds to ThingSpeak
        lnStartLogging = time.time()
        # send to the ThingSpeak data logger
        logtothing(sensornum, avgunitsused, cThingSpeakKey, adcinput)
        print "  #",sensornum,"time to TSDL=", time.time() - lnStartLogging


        # Reset the 5 minute timer
        loSensorHistory.reset5mintimer()


##############################################################
# log to Pachube.com
def logtopachube(lnSensorNum, lnAvgUnits, ApiFeedXML, lnMaxVal, rssi, thisAdc):

    if ApiFeedXML == "":
        return

    if ApiFeedXML == "0":
        return

    # Send Data to Pachube
    # feedUrl = "/api/" + ApiFeedXML + ".xml"
    # feedUrl = "/v2/feeds/" + ApiFeedXML + ".xml"
    feedUrl = int(float(ApiFeedXML))
    print "pachube feed url: " + str(feedUrl)

    # added use_https=False to this method due to update in eeml code lib
    # will set to true later when https is supported
    pac = eeml.Pachube(feedUrl, PACHUBE_KEY, use_https=False)
    # pac.update(eeml.Data(0, lnAvgUnits, minValue=0, maxValue=None, unit=eeml.Unit(name='watt', type='derivedSI', symbol='W')))
    # pac.update(eeml.Data(0, lnAvgUnits, minValue=0, maxValue=lnMaxVal))
    pac.update(eeml.Data(thisAdc, lnAvgUnits, minValue=0, maxValue=lnMaxVal))

    try:
        retVal = pac.put()
        # print "eeml update status: "+str(retVal)
        # print "Sensor# ", lnSensorNum, "logged ", lnAvgUnits, " to Pachube feed: ", ApiFeedXML
    except Exception, e:
        print "TLSM.logtopachube - eeml exception: "+str(e)
        syslog.syslog("TLSM.logtopachube exception: eeml: "+str(e))


    # update pachube with the rssi (signal strength) of the xbee sensor
    pac = eeml.Pachube(9982, PACHUBE_KEY, use_https=False)
    pac.update(eeml.Data(lnSensorNum, rssi, minValue=0, maxValue=100))

    try:
        retVal = pac.put()
        # print "eeml update status: "+str(retVal)
        # print "Sensor# ", lnSensorNum, "logged ", rssi, " dB to a Pachube signal strength feed: ", ApiFeedXML
    except Exception, e:
        print "TLSM.logtopachube - eeml exception: "+str(e)
        syslog.syslog("TLSM.logtopachube exception: eeml: "+str(e))


##############################################################
# log to Sen.se
# CJ, 03.12.2011, added logtosense() to send feeds to Sen.se
def logtosense(lnSensorNum, lnAvgUnits, ApiFeedKey):

    if ApiFeedKey == "":
        return

    if ApiFeedKey == "0":
        return

    # Send Data to Sen.se
    feedUrl = SENSEURL + SENSE_KEY

    try:
        # define a Python data dictionary
        data = {'feed_id': ApiFeedKey, 'value': lnAvgUnits}
        data_json = simplejson.dumps(data)
    
        req = urllib2.Request(feedUrl, data_json, {'content-type': 'application/json'})

        response_stream = urllib2.urlopen(req)
        response = response_stream.read()

        print response
    except:
        # Couldn't connect to  http://api.sen.se/events/?sense_key=pdd-cRQmZiaJxFz-KmbApQ
        # Couldn't connect to  http://api.sen.se/events/?sense_key=pdd-cRQmZiaJxFz-KmbApQ
        print "Couldn't connect to ", feedUrl
        syslog.syslog("TLSM.logtosense exception: Couldn't connect to " + feedUrl)


##############################################################
# log to ThingSpeak
# CJ, 05.04.2011, added logtothing() to send feeds to ThingSpeak
# http://api.thingspeak.com/update?key=U493V3CHYJS9N9FP&field1=0
# fieldnum = the ADC pin number (0,1,2,3) which will correspond to fields (1,2,3,4) in Thingspeak
def logtothing(lnSensorNum, lnAvgUnits, lcThingSpeakKey, fieldnum):

    if lcThingSpeakKey == "":
        return

    # Send Data to ThingSpeak
    feedUrl = THINGSPEAKURL + ":80"
    # feedUrl = THINGSPEAKURL
    fieldname = "field" + str(fieldnum +1)

    try:
        # define a Python data dictionary
        # print "before setup"
    	params = urllib.urlencode({fieldname : lnAvgUnits,'key':'U493V3CHYJS9N9FP'})
        headers = {"Content-type": "application/x-www-form-urlencoded","Accept": "text/plain"}

        conn = httplib.HTTPConnection(feedUrl)
        # print "before conn.request"
        conn.request("POST", "/update", params, headers)

        # print "before response"
        response = conn.getresponse()
        data = response.read()

        # print "ThingSpeak response", data
	conn.close()

    except Exception, e:
        print "Exception: ", feedUrl, " - ", str(e)
        syslog.syslog("TLSM.logtothing exception: " + feedUrl + " - " + str(e))



##############################################################
# log to the local CSV file
def logtocsv(lnSensorNum, lnAvgUnits, loLogfile):

        # Lets log it! Seek to the end of our log file
        if loLogfile:
            loLogfile.seek(0, 2) # 2 == SEEK_END. ie, go to the end of the file
            loLogfile.write(time.strftime("%Y %m %d, %H:%M")+", "+
                          str(lnSensorNum)+", "+
                          str(lnAvgUnits)+"\n")
            loLogfile.flush()
            # print "Sensor# ", lnSensorNum, "logged ", lnAvgUnits, " to ", loLogfile.name


##############################################################
# log to the SOAP based Tinaja data logger service
def logtotinaja(lnSensorNum, lnLogVal, apiKey):

    return 
    
    if apiKey == "":
        return

    # print lnLogVal, apiKey
    try:
        insertResult = client.service.insertLog(apiKey, lnLogVal)

        # Inserted all right?
        if insertResult == "Inserted":
            what= ""
            # print "Data inserted OK"
            # print "Sensor# ", lnSensorNum, "logged ", lnLogVal, " to Tinaja data logger: ", apiKey

        else:
            print "Error:", insertResult
    except:
        print "Couldn't connect to ", TINAJALOGURL
        syslog.syslog("TLSM.logtotinaja exception: Couldn't connect to " + TINAJALOGURL)

        
##############################################################
# future concept for device identity
def logtoevrythng(lnSensorNum, lnLogVal, apiKey): 
    # https://evrythng.net/adi 
    return

##############################################################
def twitterit(u, p, message):
    api = twitter.Api(username=u, password=p)
    print "Logging on with: ", u , " - ", p
    try:
        status = api.PostUpdate(message)
        print "%s just posted: %s" % (status.user.name, status.text)
    except UnicodeDecodeError:
        print "Your message could not be encoded.  Perhaps it contains non-ASCII characters? "
        print "Try explicitly specifying the encoding with the  it with the --encoding flag"
    except:
        print "Couldn't connect, check network, username and password!"


##############################################################
def addwhistory(loSensHist, newunits):
    # 03.14.2011, CJ - chgd to match addunithistory()
    loSensHist.lasttime = time.time()   # Note time of last data acquisition
    loSensHist.addvalue(newunits)      # Accumulate data point to be averaged

    ## Add Watthr to sensorhistory
    ## add up the delta-watthr used since last reading
    ## Figure out how many watt hours were used since last reading
    #elapsedseconds = time.time() - loSensHist.lasttime
    #dwatthr = (newwatts * elapsedseconds) / (60.0 * 60.0)  # 60 seconds in 60 minutes = 1 hr
    #loSensHist.lasttime = time.time()
    # print ">>       Wh used by ",loSensHist.sensornum," in last ",elapsedseconds," seconds: ",dwatthr
    #loSensHist.addwatthr(dwatthr)


##############################################################
def addunithistory(loSensHist, newunits):
    # 02.18.2011 tps Accumulate data point that will count toward 5 minute average.
    loSensHist.lasttime = time.time()   # Note time of last data acquisition
    loSensHist.addvalue(newunits)      # Accumulate data point to be averaged

    ## Add newunits to sensorhistory
    ## add up the newunits used since last reading
    ## Figure out how many units were used since last reading
    #elapsedseconds = time.time() - loSensHist.lasttime
    #thisvalue = (newunits * elapsedseconds) / (60.0 * 60.0)  # 60 seconds in 60 minutes = 1 hr
    #loSensHist.lasttime = time.time()
    ## print ">>    Units used by ",loSensHist.sensornum," in last ",elapsedseconds," seconds: ",thisvalue


##############################################################
def calctemp(xb):
    try:
        mVolts = xb.analog_samples[0][1]  # Report the millivolts from the TMP36
    except Exception, e:
        print "calctemp exception: "+str(e)
        syslog.syslog("TLSM.calctemp exception: "+str(e))
        return 0

    # tempC = mVolts * 0.1              # Convert millivolts to Celcius
    voltage = mVolts * 3.3 / 1024       # Convert millivolts to Celcius
    tempC = (voltage - .5) * 100        # Convert millivolts to Celcius

    tempF = math.floor(tempC * 9 / 5 + 32)        # Convert to Fehrenheit

    # Print formated tempurature readings
    # print tempC, "C \t", tempF, "F - ", mVolts, voltage
    return tempF


##############################################################
def getmVolts(xb, Adc):
    # xb = the xbee object
    # Adc = Analog/Digital converted number [0,1,2,3]

    try:
        mV = xb.analog_samples[0][Adc]  # Report the millivolts from the defined Adc input

    except Exception, e:
        print "getmVolts exception: "+str(e)
        syslog.syslog("TLSM.getmVolts exception: "+str(e))
        return 0

    return mV


##############################################################
def calcfsr(xb):
    try:
        mVolts = xb.analog_samples[0][1]  # Report the millivolts from the FSR
    except Exception, e:
        print "calcfsr exception: "+str(e)
        syslog.syslog("TLSM.calcfsr exception: "+str(e))
        return 0

    pressure = mVolts
    return pressure


##############################################################
def calcgas(xb):
    try:
        mVolts = xb.analog_samples[0][2]  # Report the millivolts from the Gas Sensor
    except Exception, e:
        print "calcgas exception: "+str(e)
        syslog.syslog("TLSM.calcgas exception: "+str(e))
        return 0

    # eventually we might want to determine a threshold and send a level like 0,1,2,3
    gaslevel = mVolts
    return gaslevel


##############################################################
def calcwatts(xb):
    try:
        # we'll only store n-1 samples since the first one is usually messed up
        voltagedata = [-1] * (len(xb.analog_samples) - 1)
        ampdata = [-1] * (len(xb.analog_samples ) -1)
        # grab 1 thru n of the ADC readings, referencing the ADC constants
        # and store them in nice little arrays
        for i in range(len(voltagedata)):
            voltagedata[i] = xb.analog_samples[i+1][VOLTSENSE]
            ampdata[i] = xb.analog_samples[i+1][CURRENTSENSE]
            # print "calcwatts: ", xb.address_16, voltagedata[i], ampdata[i], " | ", xb.analog_samples
            # print "calcwatts: ", xb.address_16, voltagedata[i], ampdata[i]

        # get max and min voltage and normalize the curve to '0'
        # to make the graph 'AC coupled' / signed
        min_v = 1024     # XBee ADC is 10 bits, so max value is 1023
        max_v = 0
        for i in range(len(voltagedata)):
            if (min_v > voltagedata[i]):
                min_v = voltagedata[i]
            if (max_v < voltagedata[i]):
                max_v = voltagedata[i]

        # figure out the 'average' of the max and min readings
        avgv = (max_v + min_v) / 2
        # also calculate the peak to peak measurements
        vpp =  max_v-min_v

        for i in range(len(voltagedata)):
            #remove 'dc bias', which we call the average read
            voltagedata[i] -= avgv
            # We know that the mains voltage is 120Vrms = +-170Vpp
            voltagedata[i] = (voltagedata[i] * MAINSVPP) / vpp

        # normalize current readings to amperes
        for i in range(len(ampdata)):
            # VREF is the hardcoded 'DC bias' value, its
            # about 492 but would be nice if we could somehow
            # get this data once in a while maybe using xbeeAPI
            if vrefcalibration[xb.address_16]:
                ampdata[i] -= vrefcalibration[xb.address_16]
            else:
                ampdata[i] -= vrefcalibration[0]

            # the CURRENTNORM is our normalizing constant
            # that converts the ADC reading to Amperes
            ampdata[i] /= CURRENTNORM

        #print "Voltage, in volts: ", voltagedata
        #print "Current, in amps:  ", ampdata

        # calculate instant. watts, by multiplying V*I for each sample point
        wattdata = [0] * len(voltagedata)
        for i in range(len(wattdata)):
            wattdata[i] = voltagedata[i] * ampdata[i]

        # sum up the current drawn over one 1/60hz cycle
        avgamp = 0
        # 16.6 samples per second, one cycle = ~17 samples
        # close enough for govt work :(
        for i in range(17):
            avgamp += abs(ampdata[i])
        avgamp /= 17.0

        # sum up power drawn over one 1/60hz cycle
        avgwatt = 0
        # 16.6 samples per second, one cycle = ~17 samples
        for i in range(17):         
            avgwatt += abs(wattdata[i])
        avgwatt /= 17.0
    
        return avgwatt
    except:
        return 0


##############################################################
def islogcurrent(lofilename):

    if lofilename == None:
        return false

    TimeStamp = "%s" % (time.strftime("%Y%m%d"))
    checkname = "/opt/www/tinajalog"+TimeStamp+".csv"

    if lofilename == checkname:
        return True
    else:
        return False


##############################################################
def getlogfile():
# open our datalogging file
# CJ, 05.13.2011, included /logs/ directory under www

    TimeStamp = "%s" % (time.strftime("%Y%m%d"))
    # print "TimeStamp", TimeStamp 
    filename = "/opt/www/logs/tinajalog"+TimeStamp+".csv"   # where we will store our flatfile data

    lfile = None
    try:
        lfile = open(filename, 'r+')
    except IOError:
        # didn't exist yet
        lfile = open(filename, 'w+')
        lfile.write("#Date, time, sensornum, value\n");
        lfile.flush()

    return lfile


##############################################################
def getDevice(devicesTree, deviceid):
    for device in devicesTree.findall('device'):
        if device.get('id') == deviceid:
            return device

    return None 


##############################################################
def getSetting(settingsTree, settingid):
    for setting in settingsTree.findall('setting'):
        if setting.get('id') == settingid:
            return setting

    return None

##############################################################
def getService(servicesTree, serviceid):
    for service in serviceTree.findall('service'):
        if service.get('id') == serviceid:
            return service

    return None


##############################################################
# put this at the end
# the 'main loop' runs once a second or so

# open our datalogging file
logfile = getlogfile()
print "Log file "+logfile.name+" opened..."

# load sensor history from the logfile
sensorhistories = sensorhistory.SensorHistories(logfile)
# print "Sensor history: ", sensorhistories
print "Sensor history loaded..."


syslog.syslog("<<<  Starting the Tinaja Labs Sensor Manager (TLSM)  >>>")
print "The main loop is starting..."
while True:
    mainloop(None)

    if islogcurrent(logfile.name) == False:
        logfile = getlogfile()
        # print "current log file=", logfile.name

