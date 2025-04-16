import json
from dataclasses import fields
from typing import Dict, Any, Type, Set
from data_model import Device, Port, Vlan
from xmlTranslate import xml_info as xml_info

from api_interactions import GNS3ApiClient
from topology_builder import TopologyBuilder

from connections import connections
from link_builder import LinkBuilder

import subprocess
import os
import zipfile
import argparse
import platform
import datetime
import random

import paramiko
from scp import SCPClient

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

def run_scan(path, adapterNameorId = "Wi-Fi"):
    if os.name == 'posix':
        subprocess.run(["../Publish/WeConfig", "dicover", "--adapterNameOrId",\
                         adapterNameorId, "--useMdns", "--useIpConfig", "-p", path])
    elif os.name == 'nt':
        subprocess.run(['..\Publish\WeConfig.exe', "discover", "--adapterNameOrId",\
                         adapterNameorId, "--useMdns", "--useIpConfig", "-p", path])
        #Command to run weconfig in windows! 

def run_backup(path, ip):
    if os.name == 'posix':
        subprocess.run(["../Publish/WeConfig", "backup", "-s", ip, "-p", path])
    elif os.name == 'nt':
        subprocess.run(['../Publish/WeConfig.exe', "backup", "-s", ip, "-p", path])
        #Command to run weconfig in windows!

def transfer_file(ssh_client):
    scp = SCPClient(ssh_client.get_transport())
    scp.put(f'{unique_folder}', recursive=True,remote_path='~/NDT/project_files/')
    scp.close()

def set_config(unique_folder, device, ssh_client):
    ssh_client.exec_command(f'./restore.sh admin admin device.name ./NDT/project_files/{unique_folder}/Configuration Backups/\
                            {device.id}/{get_newest_file(unique_folder + "/Configuration Backups/" + device.id)}')

 

def extract_zip(zip_path, extract_to=None):

    # If no extraction path is provided, extract to the same directory as the ZIP file
    if extract_to is None:
        extract_to = os.path.dirname(os.path.abspath(zip_path))

    # Extract the files
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
        
    print(f"Extracted ZIP archive to {extract_to}")

def create_unique_folder(base_path: str, prefix: str) -> str:
    """
    Creates a unique timestamped folder and returns its path.
    """
    # Generate unique folder name with timestamp
    timestamp = datetime.datetime.now().strftime("%y%m%d_%H%M")
    folder_name = f"{prefix}_{timestamp}"
    folder_path = os.path.join(base_path, folder_name)
    
    # Create the folder
    os.makedirs(folder_path, exist_ok=True)
    print(f"Folder ready: {folder_path}")
    
    return folder_path

def get_newest_file(directory):
    # Initialize variables to keep track of the newest file and its timestamp
    newest_file = None
    newest_timestamp = None
    
    # Iterate over each file in the directory
    for file in os.listdir(directory):
        # Extract timestamp from file name if it matches the expected format
        try:
            timestamp = datetime.strptime(file, "%Y-%m-%dT%H_%M_%SZ.json")
            
            # Update newest file and timestamp if current file is newer
            if newest_timestamp is None or timestamp > newest_timestamp:
                newest_file = file
                newest_timestamp = timestamp
        except ValueError:
            # Skip files that do not match the expected format
            continue
    
    return newest_file


def get_newest_file(file_list):
     # Initialize variables to keep track of the newest file and its timestamp
    newest_file = None
    newest_timestamp = None
   
   # Iterate over each file in the list
    for file in file_list:
    # Extract timestamp from file name
        timestamp = datetime.strptime(file, "%Y-%m-%dT%H_%M_%SZ.json")
     
     # Update newest file and timestamp if current file is newer
    if newest_timestamp is None or timestamp > newest_timestamp:
        newest_file = file

    return newest_file



print("Testing weconfig CLI tool...")
print("-" * 50)

project = "test.nprj"

run_scan(project, "Ethernet 2")
run_backup(project, "169.254.1.1/16")

# Example usage
unique_folder = create_unique_folder("./topologies", "project")
extract_zip(project, f"{unique_folder}")
print(f"Extracted project to {unique_folder}")

# list to store devices
device_list: list[Device] = []

#path = f"{unique_folder}\Project.xml"
xml = xml_info(f"{unique_folder}\Project.xml")
xml.findDevices()

devices_dict = xml.device_list
#devices_dict = {}

#append cloud device to the devices_dict
devices_dict["cloud"] = {"name": "cloud", "id": "cloud", "family": "cloud", "ports": {"virbr0": {}}}

print(devices_dict)

# Iterate through the dictionary and create Device objects
for device_id, device_data in devices_dict.items():
    # Extract ports data for separate handling
    # pop() removes the key from the dictionary
    ports_data = device_data.pop("ports", {})
    vlans_data = device_data.pop("vlans", {})
    
    try:

        # validate dictionary keys
        if device_id != "cloud":
            validate_dict_keys(device_data, Device, ["ports", "vlans"])
        device = Device(**device_data)

        # Process ports
        for port_id, port_data in ports_data.items():
            # validate dictionary keys
            if device_id != "cloud":
                validate_dict_keys(port_data, Port)
            port = Port(**port_data)
            device.ports[port_id] = port

        # Process vlans
        for vlan_id, vlan_data in vlans_data.items():
            # validate dictionary keys
            if device_id != "cloud":
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

    
    print("-" * 50)

print("\nTesting GNS3 API and Topology Builder")
print("-" * 50)

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

# BUILD DEVICES
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

# Parse connections from XML
conn = connections(f"{unique_folder}\Project.xml")
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

ssh = paramiko.SSHClient()
ssh.load_system_host_keys()
try:
        ssh.connect(hostname='10.2.100.235', username='it')
except Exception:
        print('fel')

transfer_file(ssh)

api_client.start_nodes(project_id)

for device in device_list:
    set_config(unique_folder, device, ssh)
#TODO Ny anslutning till server. 
#TODO for device in device_list: 
#TODO ssh.exec_command('./restore.sh admin admin device.name ./NDT/project_files/{unique_folder}/Configuration Backups/{device.id}/{find latest backup}')
# 
#   