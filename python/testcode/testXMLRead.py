# testXML.py
# exaqmples: http://www.doughellmann.com/PyMOTW/xml/etree/ElementTree/parse.html#parsing-an-entire-document 

from xml.etree.ElementTree import ElementTree


def getDevice(devicesTree, deviceid):
    for device in devicesTree.findall('device'):
        if device.get('id') == deviceid:
            return device

    return None

thisTree = ElementTree()
thisTree.parse("tinajaconfig.xml")

for node in thisTree.iter():
    # print the whole tree
    # print node.tag, node.attrib
    pass

print ""

#Get the root node
tinajaRoot = thisTree.getroot()

deviceslist = tinajaRoot.find('./devices')
thisRadio = 1

thisDevice = getDevice(deviceslist, str(thisRadio))

if thisDevice != None:
    print "This device found: ", thisDevice.get('desc')
    print "== Device Settings:"
    datafeedslist = thisDevice.find('./datafeeds')
    if datafeedslist != None:
        for datafeed in datafeedslist:
            print "Device data feeds: ", datafeed.attrib.get("service"), datafeed.attrib.get("id")

else:
    print "This device not found..."


print "== Settings:"
settingslist = tinajaRoot.find('./settings')
if settingslist != None:
    for setting in settingslist:
        if setting.tag == "serial":
            print "Setting: ", setting.tag, setting.attrib.get("port"), setting.attrib.get("baudrate")
        if setting.tag == "power":
            print "Setting: ", setting.tag, setting.attrib.get("currentsense"), setting.attrib.get("voltsense"), setting.attrib.get("mainvpp")


print "==  Services:"
serviceslist = tinajaRoot.find('./services')
if serviceslist != None:
    for service in serviceslist:
        print "Service: ", service.attrib.get("name"), service.attrib.get("url"), service.attrib.get("apikey")


print "==  Devices:"
deviceslist = tinajaRoot.find('./devices')
if deviceslist != None:
    for device in deviceslist:
        print "Device: ", device.attrib.get("id"), device.attrib.get("desc")

        print "==  Feeds:"
        datafeedslist = device.find('./datafeeds')
        if datafeedslist != None:
            for feed in datafeedslist:
                if feed.attrib.get("service") == "pachube":
                    print "Datafeed: ", feed.attrib.get("id"), feed.attrib.get("desc")


def prettify(elem):
    """Return a pretty-printed XML string for the Element.
    """
    rough_string = ElementTree.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

