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
            if 'AggregatePortConnection' in child.tag:
                #Input dict of DeviceId's in connection dictionary
                if connId not in self.conn_dict: 
                    self.conn_dict['connection'+str(connId)] = {}
                self.conn_dict['connection'+str(connId)] = child.attrib

                for interface in child.iter():
                    #Add source device port to the correct connection
                    if 'SourceDevicePort' in interface.tag:
                        sourceDevice = interface[0].attrib.get('Name')
                        if sourceDevice is not None:
                            if sourceDevice.startswith('ETH '):
                                sourceDevice = sourceDevice.lower().replace(' ', '')
                                sourceDevice = sourceDevice[3:]
                                self.conn_dict['connection'+str(connId)]['source_device_port'] = int(sourceDevice)

                            if sourceDevice.lower().startswith('dsl'):
                                self.conn_dict.pop('connection'+str(connId)) #Remove DSL connection from dsl
                                print(f'Connection {connId} removed: DSL link')
                            if sourceDevice.startswith('eth'):
                                sourceDevice = sourceDevice[3:]
                                self.conn_dict['connection'+str(connId)]['source_device_port'] = int(sourceDevice)

                    #Add target device port to the correct connection
                    if 'TargetDevicePort' in interface.tag:
                        targetDevice = interface[0].attrib.get('Name')
                        if targetDevice is not None:
                            if targetDevice.startswith('ETH '):
                                targetDevice = targetDevice.lower().replace(' ', '')
                                targetDevice = targetDevice[3:]
                                self.conn_dict['connection'+str(connId)]['target_device_port'] = int(targetDevice)
                            if targetDevice.startswith('DSL '):
                                pass 

                            if targetDevice.startswith('eth'):
                                targetDevice = targetDevice[3:]
                                self.conn_dict['connection'+str(connId)]['target_device_port'] = int(targetDevice)                            
                connId+=1
        self.prettyPrint()

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
    #.prettyPrint()
