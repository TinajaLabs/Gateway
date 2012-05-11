# build an xml file

from xml.etree.ElementTree import ElementTree, Element, SubElement, Comment
from ElementTree_pretty import prettify
import sys


def makeDevice(id, active, devicekey, desc, vrefcal):
    # build a device element
    device = SubElement(devices, 'device',{'id':id,'active':active,'devicekey':devicekey, 'desc':desc, 'vrefcal':vrefcal})
    makeDataFeeds(device)
    return ""

def makeDataFeeds(device):
    datafeeds = SubElement(device, 'datafeeds')
    datafeed = SubElement(datafeeds, 'datafeed', {'id':"0", 'feedkey':"", 'feedapi':"", 'service':"pachube", 'desc':""})
    datafeed = SubElement(datafeeds, 'datafeed', {'id':"1", 'feedkey':"", 'feedapi':"", 'service':"pachube", 'desc':""})
    datafeed = SubElement(datafeeds, 'datafeed', {'id':"2", 'feedkey':"", 'feedapi':"", 'service':"pachube", 'desc':""})
    datafeed = SubElement(datafeeds, 'datafeed', {'id':"3", 'feedkey':"", 'feedapi':"", 'service':"pachube", 'desc':""})
    # makeServiceFeeds(datafeed)
    return ""

def makeServiceFeeds(datafeed):
    ServiceFeed = SubElement(datafeed, 'service')
    ServiceFeed.text = "pachube"
    return ""


##############################################################
def writeconfig(configString):
    # open the xml config file
    filename = "tinajaconfigGen.xml"

    cfile = open(filename, 'w')
    cfile.write(configString)
    cfile.close()

#####################################################################
tinajaTop = Element('tinaja')
comment = Comment('Generated config file for TinajaLabs')
tinajaTop.append(comment)

# set up the settings
settings = SubElement(tinajaTop, 'settings')
setserial = SubElement(settings, 'serial',{'baudrate':"9600", 'port':"/dev/ttyS1"})
setpower = SubElement(settings, 'power',{'currentsense':"4", 'currentnorm':"15.5", 'voltsense':"0", 'mainvpp':"340"})

# set up the services
services = SubElement(tinajaTop, 'services')
service1 = SubElement(services, 'service',{'name':"pachube", 'url':"/v2/feeds/", 'apikey':"e7d7befa77e795a688c5d0b6c7a3ddef95012e2e2e57062be4c7d175d2901651", 'uname':"janedoe", 'passw':"xyz" })
service2 = SubElement(services, 'service',{'name':"thingspeak", 'url':"api.thingspeak.com", 'apikey':"U493V3CHYJS9N9FP", 'uname':"janedoe", 'passw':"xyz" })
service3 = SubElement(services, 'service',{'name':"opensense", 'url':"http://api.sen.se/events/?sense_key=", 'apikey':"pdd-cRQmZiaJxFz-KmbApQ", 'uname':"janedoe", 'passw':"xyz" })
service4 = SubElement(services, 'service',{'name':"tinajalabs", 'url':"http://jumano.com/tinajadl/datalogger.asmx", 'apikey':"xyz", 'uname':"janedoe", 'passw':"xyz" })
service5 = SubElement(services, 'service',{'name':"twitter", 'url':"http://www.google.com", 'apikey':"xyz", 'uname':"chrisjx", 'passw':"xyz" })

devices = SubElement(tinajaTop, 'devices')

# id,active,feedkey,desc,vrefcal
test = makeDevice("1","1","9666","Power Meter - Tweet-a-Watt","488")
test = makeDevice("2","1","9709","Back Porch Radio","0")
test = makeDevice("3","1","9668","Power Meter - Tweet-a-Watt","487")
test = makeDevice("4","1","9669","Power Meter - Tweet-a-Watt","485")
test = makeDevice("5","1","10267","Natural Gas Sensor - Dining room","0")
test = makeDevice("6","0","10258","unused","0")
test = makeDevice("7","1","24660","Office Multi-sensor PCB1","0")
test = makeDevice("8","1","25131","Bed room Multi-sensor PCB1","0")
test = makeDevice("9","1","25133","Guest room Multi-sensor PCB1","0")
test = makeDevice("10","1","25134","Living Room Multi-sensor PCB1","0")
test = makeDevice("11","1","25135","Experimental solar power tracking","0")
test = makeDevice("12","0","","Power Meter - Tweet-a-Watt","486")
test = makeDevice("13","0","","router receiver","0")
test = makeDevice("14","0","","Terence","0")
test = makeDevice("15","0","29631","unused","0")
test = makeDevice("16","1","","Garage Multi-sensor PCB1","0")
test = makeDevice("17","0","","unused","0")
test = makeDevice("18","0","","unused","0")
test = makeDevice("19","0","","unknown","0")
test = makeDevice("20","0","","Terence","0")
test = makeDevice("21","0","","unknown","0")


# rough_string = ElementTree.tostring(tinajaTop, 'utf-8')
# reparsed = minidom.parseString(rough_string)
# prettyXML = reparsed.toprettyxml(indent="  ")

prettyXML = prettify(tinajaTop)

writeconfig(prettyXML)
# print prettify(tinajaTop)
print prettyXML
print "done... "
