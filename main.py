import json
from dataclasses import fields
from typing import Dict, Any, Type, Set
from data_model import Device, Port, Vlan
from xmlTranslate import xml_info as xml_info

def validate_dict_keys(data_dict: Dict[str, Any], dataclass_type: Type, exclude_fields: list = None) -> bool:
    """
    Validate that dictionary keys match dataclass fields (excluding specified fields).
    Raises ValueError if there's any mismatch.
    """
    exclude_fields = exclude_fields or []
    dataclass_fields = {field.name for field in fields(dataclass_type) if field.name not in exclude_fields}
    dict_keys = set(data_dict.keys())
    
    if dataclass_fields != dict_keys:
        raise ValueError(f"Dictionary keys don't exactly match {dataclass_type.__name__} fields")
    
    return True


#TODO set the correct base mac address in gns3 so that it matches the one in the xml file

# 1) 
#TODO script should be run from command line with arguments that specify the physical topology folder and network to scan
# 1) load from project foler or 2) load from network scan
#TODO check if folder is empty, if it is do the scan
#TODO check if physical topology folder already exists, if so, delete it

#TODO create folder for physical topology
#TODO perform scan of network using weconfig cli tool
#TODO perform backup of all devices in network using weconfig cli tool
#TODO unzip project into physical topology folder
#TODO create project in GNS3 using GNS3 API
#TODO create devices in GNS3 using GNS3 API
#TODO create links between devices in GNS3 using GNS3 API
#TODO apply configuration to devices in GNS3 using GNS3 API
#TODO start devices in GNS3 using GNS3 API

#TODO wait for user input
#TODO check if virtual topology folder already exists, if so, delete it
#TODO create folder for virtual topology
#TODO scan network using weconfig cli tool (this will always use the 169.254.1.1/16 network)
# 
#TODO backup all devices in network using weconfig cli tool
#TODO unzip project into project 2 folder
#TODO check if the configuration files are the same as the ones in project 1
#TODO apply configuration to devices in physical topology if the configuration changed
# dont check if it changed, just apply it


# list to store devices
device_list: list[Device] = []
xml = xml_info(r'sample_xml\Project-3.1.xml')
xml.findDevices()

devices_dict = xml.device_list

# Iterate through the dictionary and create Device objects
for device_id, device_data in devices_dict.items():
    # Extract ports data for separate handling
    # pop() removes the key from the dictionary
    ports_data = device_data.pop("ports", {})
    vlans_data = device_data.pop("vlans", {})
    
    try:
        # validate dictionary keys
        validate_dict_keys(device_data, Device, ["ports", "vlans"])
        device = Device(**device_data)
        
        # Process ports
        for port_id, port_data in ports_data.items():
            # validate dictionary keys
            validate_dict_keys(port_data, Port)
            port = Port(**port_data)
            device.ports[port_id] = port

        # Process vlans
        for vlan_id, vlan_data in vlans_data.items():
            # validate dictionary keys
            validate_dict_keys(vlan_data, Vlan)
            vlan = Vlan(**vlan_data)
            device.vlans[vlan_id] = vlan
        
        # Add the device to our list
        device_list.append(device)
        
    except Exception as e:
        print(f"Error creating device {device_id}: {e}")
    finally:
        # Put ports back in device_data for future reference
        device_data["ports"] = ports_data

# Print device details
for device in device_list:
    print(f"\nDevice Details for: {device.name}")
    for attr, value in device.__dict__.items():
        if attr != "ports" and attr != "vlans":  # Handle port and separately
            print(f"{attr}: {value}")
    
    print("VLANs:")
    for vlan_id, vlan in device.vlans.items():
        #print(f"  VLAN: {vlan}")
        for vlan_attr, vlan_value in vlan.__dict__.items():
            print(f"    {vlan_attr}: {vlan_value}")

    print("Ports:")
    for port_id, port in device.ports.items():
        #print(f"  Port: {port}")
        for port_attr, port_value in port.__dict__.items():
            print(f"    {port_attr}: {port_value}")
    
    print("-" * 50)

print("\nTesting GNS3 API and Topology Builder")
print("-" * 50)

from api_interactions import GNS3ApiClient
from topology_builder import TopologyBuilder

print("Testing connection to GNS3 server...")
api_client = GNS3ApiClient()
projects = api_client.get_projects()
print(f"Connection successful! Found {len(projects)} projects.")

for dict in projects:
    if dict["name"] == "auto_1":
        id = dict["project_id"]
        api_client.delete_project(id)
        print("Deleted project auto_1")

print("\nBuilding network topology in GNS3...")
print("-" * 50)

# Create or get project and build devices
topology_builder = TopologyBuilder()

# List available templates to help with configuration
#topology_builder.list_available_templates()

try:
    node_mapping = topology_builder.build_topology(device_list)
    
    print(f"Successfully created topology with {len(node_mapping)} devices")
    
    # Save node mapping for link creation (secondary goal)
    with open("node_mapping.json", "w") as f:
        json.dump(node_mapping, f, indent=2)
        
except Exception as e:
    print(f"Error building topology: {str(e)}")

print("\nBuilding links between devices...")
print("-" * 50)

from connections import connections
from link_builder import LinkBuilder

# Parse connections from XML
conn = connections(r'sample_xml\Project-3.1.xml')
conn.getConnections()
connection_data = conn.conn_dict

# Create link builder
link_builder = LinkBuilder(api_client=topology_builder.api_client)

try:
    # Get project ID (reuse the same project)
    project_id = topology_builder.create_or_get_project()
    
    # Build links
    links = link_builder.build_links(project_id, connection_data, node_mapping)
    
    print(f"Successfully created {len(links)} links")
    
except Exception as e:
    print(f"Error building links: {str(e)}")


#TODO 