import xml.etree.ElementTree as ET
import json
import re

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
        #self.prettyPrint()

    def deviceList(self, child): 
        self.device_list[child.attrib.get('Id')] = device = {}
        self.device_list[child.attrib.get('Id')]['id'] = child.attrib.get('Id') 
        addresses = ''
        device['position'] = {}
        
        for hostInfo in child.iter():
            if 'Hostname' in hostInfo.tag:
                self.device_list[child.attrib.get('Id')]['name'] = hostInfo.text
            if 'Position' in hostInfo.tag:
                x_str = hostInfo.attrib['X'].replace(',', '.')
                y_str = hostInfo.attrib['Y'].replace(',', '.')
                pos = round(float(x_str), 2), round(float(y_str), 2)
                self.device_list[child.attrib.get('Id')]['position'] = tuple(pos)
            if 'ManagementIpAddress' in hostInfo.tag:
                addresses = hostInfo.text
            if 'ChassisId' in hostInfo.tag:
                base_mac = hostInfo.text
        device['family'] = child.attrib.get('Family')
        device['model']= child.attrib.get('Model')
        device['image' ]= f"WeOs{child.attrib.get('FirmwareVersion')}"
        self.device_list[child.attrib.get('Id')]['ip_address'] = addresses
        self.device_list[child.attrib.get('Id')]['base_mac'] = base_mac

    def getVlans(self, child):
        self.device_list[child.attrib.get('Id')]['vlans'] = {}
        for vlanInfo in child.iter():
            if 'NetworkInterface' in vlanInfo.tag:
                for vlan in vlanInfo:
                    self.device_list[child.attrib.get('Id')]['vlans'][vlan.attrib.get('Name')] = {}
                    self.device_list[child.attrib.get('Id')]['vlans'][vlan.attrib.get('Name')]['name'] =  vlan.attrib.get('Name')
                    self.device_list[child.attrib.get('Id')]['vlans'][vlan.attrib.get('Name')]['address'] =  vlan[0].attrib.get('Value')
                    

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
            self.device_list[dev_id] = {'ports': {}}
        if 'ports' not in self.device_list[dev_id]:
            self.device_list[dev_id]['ports'] = {}
        if ch.get('Name') not in self.device_list[dev_id]['ports']:
            if 'eth' in ch.get('Name').lower():
                self.device_list[dev_id]['ports'][ch.get('Name')] = {}

                self.device_list[dev_id]['ports'][ch.get('Name')] = {}
                self.device_list[dev_id]['ports'][ch.get('Name')]['index'] = int(re.sub(r'[^0-9]', '', ch.get('Name').lower()))
                for mac in child.iter():
                    typ = mac.get('Type')
                    if typ is not None: 
                        self.device_list[dev_id]['ports'][ch.get('Name')]['mac_address'] = mac.text
                
                if child.attrib['Up'].lower() == 'true':
                    self.device_list[dev_id]['ports'][ch.get('Name')]['up'] = True
                elif child.attrib['Up'].lower() == 'false':
                    self.device_list[dev_id]['ports'][ch.get('Name')]['up'] = False
        
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
            return data
        else:
            data = self.device_list[dict]
            print(json.dumps(data, indent = 4))
            return data




if __name__ == "__main__":
    xml = xml_info(r'topologies\project_250416_1050\Project.xml')
    xml.findDevices()
    #print(xml.showDevices())
    print('-' * 15)
    #print(xml.showDevices())
    #print('Device: ', xml.showDevices('a80f1106-01c5-42ea-a254-47e9df0d05ec'))
    print('-' * 20)
    #print('Device: ', xml.showDevices('e92752be-9b3b-45f2-b09f-39cd65571f0f'))
    #xml.prettyPrint('7443738c-e4dc-4567-a0be-71a258b53de4')
    #
 
