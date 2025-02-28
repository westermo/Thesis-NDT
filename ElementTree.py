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
                #print('Device: ', child.attrib)
                #print('Family: ', child.attrib.get('Family'))
                print('-' * 15)
                self.deviceList(child)

    def deviceList(self, child): 
        #self.device_list.append(child.attrib.get('Family')) om lista istället för dict
        self.device_list[child.attrib.get('Id')] = {}
        self.device_list[child.attrib.get('Id')][child.attrib.get('Family')] = child.attrib.get('Model')
        return True

    def showDeviceInfo(self):
        return self.device_info

    def createDeviceInfo(self):
        for child in self.root.iter():
            if "PhysicalLayer" in child.attrib:
                #print(child.tag, child.attrib, child.text)
                for ch in child.iter():
                    if ch.get('Name') is not None:
                        print('ch: ', ch.get('Name')) 
            
            #print(child.tag, child.attrib, child.text) Bra att komma ihåg
            
            
            """if "vlan" in child.tag:
                print('VLAN:', child.attrib.get)

            for ch in child:
                if "vlan" in ch.attrib:
                    self.device_info[child.attrib.get('Id')] = {}
                    self.device_info[child.attrib.get('Id')][ch.attrib('Name')]"""

    def showDevices(self):
        return self.device_list


if __name__ == "__main__":
    xml = xml_info(r'Kod\NDT\sample_xml\Project-3.0.xml')
    xml.findDevices()
    print(xml.showDevices())
    xml.createDeviceInfo()
    #print(xml.showDeviceInfo())