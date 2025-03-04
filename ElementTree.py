import xml.etree.ElementTree as ET

class xml_info:
    def __init__(self, file_path):
        self.file_path = file_path
        self.tree = ET.parse(file_path)
        self.root = self.tree.getroot()
        self.device_list = {}
        self.device_info = {}

    def findDevices(self):
        for child in self.root.iter():
            if 'Family' in child.attrib:
                self.deviceList(child)

    def deviceList(self, child): 
        self.device_list[child.attrib.get('Id')] = {}
        for hostname in child:
            if 'Hostname' in hostname.tag:
                self.device_list[child.attrib.get('Id')]['Hostname'] = hostname.text
        self.device_list[child.attrib.get('Id')][child.attrib.get('Family')] = child.attrib.get('Model')


    def showDeviceInfo(self):
        return self.device_info

    def createDeviceInfo(self):
        dev_id = None
        for child in self.root.iter():
            if 'Family' in child.attrib:
                dev_id = child.attrib.get('Id')

            if "PhysicalLayer" in child.attrib:
                for ch in child.iter():
                    if ch.get('Name') is not None:
                        self.getPortInfo(child, ch, dev_id)


    def getPortInfo(self, child, ch, dev_id):
        if dev_id not in self.device_list:
            self.device_list[dev_id] = {'Ports': {}}
        if 'Ports' not in self.device_list[dev_id]:
            self.device_list[dev_id]['Ports'] = {}
        if ch.get('Name') not in self.device_list[dev_id]['Ports']:
            self.device_list[dev_id]['Ports'][ch.get('Name')] = {}

        self.device_list[dev_id]['Ports'][ch.get('Name')] = {}
        self.device_list[dev_id]['Ports'][ch.get('Name')]['Up'] = child.attrib['Up']
        for mac in child.iter():
            typ = mac.get('Type')
            if typ is not None: 
                self.device_list[dev_id]['Ports'][ch.get('Name')][typ] = mac.text



    def showDevices(self, dict = None):
        if dict:
            return self.device_list[dict]
        else:
            return self.device_list


if __name__ == "__main__":
    xml = xml_info(r'sample_xml\Project-3.0.xml')
    xml.findDevices()
    print(xml.showDevices())
    xml.createDeviceInfo()
    print('-' * 15)
    #print(xml.showDevices())
    print('Device: ', xml.showDevices('a80f1106-01c5-42ea-a254-47e9df0d05ec'))
    print('-' * 20)
    print('Device: ', xml.showDevices('3260052c-bf7b-41e3-9203-0716f9eb5795'))
 
