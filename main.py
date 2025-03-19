from dataclasses import fields
from typing import Dict, Any, Type, Set
from data_model import Device, Port
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

# # Example dictionary of devices
# devices_dict: Dict[str, Dict[str, Any]] = {
#     "device1": {
#         "name": "redfox-4d-31-c0",
#         "id": "a80f1106-01c5-42ea-a254-47e9df0d05ec",
#         "position": (-3.17, 8.92),
#         "family": "RedFox",
#         "model": "RedFox-5528-F4G-T24G-LV",
#         "image": "WeOS-5.24",
#         "ip_address": "198.18.2.67",
#         "net_mask": "255.255.255.0",
#         "ports": {
#             "port1": {
#                 "name": "eth1",
#                 "id": "0",
#                 "mac_address": "00:07:7C:4D:31:C1",
#                 "up": False,
#             },
#             "port2": {
#                 "name": "eth2",
#                 "id": "1",
#                 "mac_address": "00:07:7C:4D:31:C2",
#                 "up": False,
#             }
#         }
#     },
#     "device2": {
#         "name": "kompis",
#         "id": "123ad481-2a0f-4a61-8e23-1684c36f98d7",
#         "position": (-3.17, 8.92),
#         "family": "Wolverine",
#         "model": "DDW-142",
#         "image": "WeOS-5.24",
#         "ip_address": "198.18.2.201",
#         "net_mask": "255.255.255.0",
#         "ports": {
#             "port1": {
#                 "name": "ETH 1",
#                 "id": "0",
#                 "mac_address": "00:07:7C:10:87:C3",
#                 "up": True,
#             },
#             "port2": {
#                 "name": "ETH 2",
#                 "id": "1",
#                 "mac_address": "00:07:7C:10:87:C4",
#                 "up": True,
#             }
#         }
#     },
#     "device3": {
#         "name": "lynx-59-93-a0",
#         "id": "93650786-e7c9-40e9-bf90-b82808c0c569",
#         "position": (-3.17, 8.92),
#         "family": "Lynx",
#         "model": "Lynx-3510-E-F2G-P8G-LV",
#         "image": "WeOS-5.24",
#         "ip_address": "198.18.2.145",
#         "net_mask": "255.255.255.0",
#         "ports": {
#             "port1": {
#                 "name": "eth1",
#                 "id": "0",
#                 "mac_address": "00:11:B4:59:93:A1",
#                 "up": False,
#             },
#             "port2": {
#                 "name": "eth2",
#                 "id": "1",
#                 "mac_address": "00:11:B4:59:93:A2",
#                 "up": False,
#             },
#             "port3": {
#                 "name": "eth3",
#                 "id": "2",
#                 "mac_address": "00:11:B4:59:93:A3",
#                 "up": False,
#             },
#             "port4": {
#                 "name": "eth4",
#                 "id": "3",
#                 "mac_address": "00:11:B4:59:93:A4",
#                 "up": False,
#             }
#         }
#     }
# }

# list to store devices
device_list: list[Device] = []
xml = xml_info(r'sample_xml\Project-3.1.xml')
xml.findDevices()

devices_dict = xml.device_list

# Iterate through the Example dictionary and create Device objects
for device_id, device_data in devices_dict.items():
    # Extract ports data for separate handling
    # pop() removes the key from the dictionary
    ports_data = device_data.pop("ports", {})
    
    try:
        # validate dictionary keys
        validate_dict_keys(device_data, Device, ["ports"])
        device = Device(**device_data)
        
        # Process ports
        for port_id, port_data in ports_data.items():
            # validate dictionary keys
            validate_dict_keys(port_data, Port)
            port = Port(**port_data)
            device.ports[port_id] = port
        
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
        if attr != "ports":  # Handle ports separately
            print(f"{attr}: {value}")
    
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

