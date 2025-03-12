import xml.etree.ElementTree as ET
import json

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
                self.getVlans(child)
        self.createDeviceInfo()

    def deviceList(self, child): 
        self.device_list[child.attrib.get('Id')] = device = {}
        addresses = ''
        device['Position'] = {}
        for hostInfo in child.iter():
            if 'Hostname' in hostInfo.tag:
                self.device_list[child.attrib.get('Id')]['Hostname'] = hostInfo.text
            if 'Position' in hostInfo.tag:
                pos =  round(float(hostInfo.attrib['X']), 2), round(float(hostInfo.attrib['Y']), 2)
                self.device_list[child.attrib.get('Id')]['Position'] = tuple(pos)
            if 'ManagementIpAddress' in hostInfo.tag:
                addresses = hostInfo.text
        device['Family'] = child.attrib.get('Family')
        device['Model']= child.attrib.get('Model')
        device['Image' ]= f'WeOs{child.attrib.get('FirmwareVersion')}'
        self.device_list[child.attrib.get('Id')]['Addresses'] = {}
        self.device_list[child.attrib.get('Id')]['Addresses']['Management'] = addresses

    def getVlans(self, child):
        self.device_list[child.attrib.get('Id')]['vlans'] = {}
        for vlanInfo in child.iter():
            if 'NetworkInterface' in vlanInfo.tag:
                for vlan in vlanInfo:
                    #print('Vlan:!:!:!: ', vlan.attrib.get('Name'), vlan[0].attrib.get('Value'))
                    self.device_list[child.attrib.get('Id')]['vlans'][vlan.attrib.get('Name')] = vlan[0].attrib.get('Value')

    def createDeviceInfo(self):
        dev_id = None
        for child in self.root.iter():
            if 'Family' in child.attrib:
                dev_id = child.attrib.get('Id')

            if "PhysicalLayer" in child.attrib:
                for ch in child.iter():
                    if ch.get('Name') is not None:
                        self.getPortInfo(child, ch, dev_id)


    def getPortInfo(self, child, ch, dev_id): #Everything with ports 
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
        
    def showDeviceInfo(self):
        return self.device_info

    def showDevices(self, dict = None):
        if dict:
            return self.device_list[dict]
        else:
            return self.device_list
        
    def prettyPrint(self, dict = None):
        if dict == None:
            data = self.device_list
            print(json.dumps(data, indent=4))
        else:
            data = self.device_list[dict]
            print(json.dumps(data, indent = 4))



if __name__ == "__main__":
    xml = xml_info(r'sample_xml\Project-3.1.xml')
    xml.findDevices()
    #print(xml.showDevices())
    print('-' * 15)
    #print(xml.showDevices())
    #print('Device: ', xml.showDevices('a80f1106-01c5-42ea-a254-47e9df0d05ec'))
    print('-' * 20)
    #print('Device: ', xml.showDevices('e92752be-9b3b-45f2-b09f-39cd65571f0f'))
    xml.prettyPrint()
 
