import xml.etree.ElementTree as ET
import json

class connections:
    def __init__(self, file_path):
        self.file_path = file_path
        self.tree = ET.parse(file_path)
        self.root = self.tree.getroot()
        self.conn_dict = {}
    
    def getConnections(self):
        connId = 0 
        for child in self.root.iter():
            #print(child.tag)
            if 'AggregatePortConnection' in child.tag:
                #print(child.attrib)

                if connId not in self.conn_dict:
                    self.conn_dict['connection'+str(connId)] = {}
                self.conn_dict['connection'+str(connId)] = child.attrib
                #print(connId, self.conn_dict)

                 
            #print('Child.tag: ', child.tag)
                for interface in child.iter():
                    if 'SourceDevicePort' in interface.tag:
                        print(interface.tag, interface[0].attrib.get('Name'))
                        self.conn_dict['connection'+str(connId)]['source_device_port'] = interface[0].attrib.get('Name')


                    if 'TargetDevicePort' in interface.tag:
                        print(interface.tag, interface[0].attrib.get('Name'))
                        targetDevice = interface[0].attrib.get('Name')
                        #if targetDevice.startswith('ETH'): 
                            #targetDevice = targetDevice.lower().replace(' ', '')
                        print(targetDevice)
                        # self.conn_dict['connection'+str(connId)]['target_device_port'] = targetDevice
            connId+=1

    def prettyPrint(self, dict = None): 
        if dict == None:
            data = self.conn_dict
            print(json.dumps(data, indent=4))
            return data
        else:
            data = self.conn_dict[dict]
            print(json.dumps(data, indent = 4))
            return data

if __name__ == '__main__':
    conn = connections(r'sample_xml\Project-3.1.xml')
    conn.getConnections()
    conn.prettyPrint()
