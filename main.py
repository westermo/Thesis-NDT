from typing import Dict, Any, Type, Set
from data_model import Device, Port, Vlan
from dataclasses import fields
from scp import SCPClient
from datetime import datetime
import paramiko



import json
import time
import subprocess
import os
import zipfile
import argparse
import platform
import random
import shutil
import logging

from xmlTranslate import xml_info as xml_info
from link_builder import LinkBuilder
from connections import connections
from api_interactions import GNS3ApiClient
from topology_builder import TopologyBuilder

# On Oskar's computer, the path to the new WeConfig is:
# ~\AppData\Local\WeConfig-dev-cli\current\WeConfig.exe

# On the server, the path to the new WeConfig is the same

def cleanup_files(topologies_path="./topologies"):
    """Remove all content in the topologies directory and the test.nprj file."""
    
    try:
        # Clean up topologies directory
        if os.path.exists(topologies_path):
            # Remove all content but keep the directory itself
            for item in os.listdir(topologies_path):
                item_path = os.path.join(topologies_path, item)
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                except Exception as e:
                    logger.error(f"Failed to delete {item_path}: {str(e)}")
                    
        # Remove test.nprj file
        test_file = "./test.nprj"
        if os.path.exists(test_file):
            try:
                os.remove(test_file)
                logger.debug(f"Removed {test_file}")
            except Exception as e:
                logger.error(f"Failed to delete {test_file}: {str(e)}")
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
 
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

def transfer_file(ssh_client, folder_path):
    logger.info(f"Transferring folder {folder_path} via SCP")
    try:
        scp = SCPClient(ssh_client.get_transport())
        scp.put(f'{folder_path}', recursive=True, remote_path='~/NDT/project_files/')
        scp.close()
        logger.info(f"Successfully transferred {folder_path}")
    except Exception as e:
        logger.error(f"Failed to transfer {folder_path}: {str(e)}")
        raise

def get_file(ssh_client, file_path):
    logger.info(f"Transferring file {file_path} via SCP")
    try:
        scp = SCPClient(ssh_client.get_transport())
        scp.get(remote_path=file_path, local_path='./')
        scp.close()
        logger.info(f"Successfully transferred {file_path}")
    except Exception as e:
        logger.error(f"Failed to transfer {file_path}: {str(e)}")
        raise

def set_config(folder_path, device, ssh_client):
    """Set device configuration using the newest backup file"""
    remote_path = f"~/NDT/project_files/{folder_path}/Configuration\ Backups/{device.id}/"
    
    # Execute command to find newest file on remote server
    stdin, stdout, stderr = ssh_client.exec_command(f"ls -t {remote_path}*.json | head -1")
    error = stderr.read().decode('utf-8').strip()
    if error:
        logger.error(f"Error finding config file: {error}")
        return
    
    config_file = stdout.read().decode('utf-8').strip()
    if not config_file:
        logger.error(f"No config file found in {remote_path}")
        return
    
    # Extract just the filename from the full path
    config_filename = os.path.basename(config_file)
    
    # Build and execute restore command
    mac_parts = device.base_mac.split(":")
    last_three_octets = mac_parts[-3:]
    mac_suffix = "-".join(last_three_octets)
    device_hostname = f"{device.family}-{mac_suffix}.local"
    command = f'~/restore.sh admin admin {device_hostname} {remote_path}{config_filename}'
    logger.debug(f'Executing command: {command}')
    
    # Execute the command
    stdin, stdout, stderr = ssh_client.exec_command(command)
    
    # Get both outputs
    output = stdout.read().decode('utf-8')
    stderr_output = stderr.read().decode('utf-8')
    
def get_hostname(device):
    """Get the hostname of the device"""
    mac_parts = device.base_mac.split(":")
    last_three_octets = mac_parts[-3:]
    mac_suffix = "-".join(last_three_octets)
    device_hostname = f"{device.family}-{mac_suffix}.local"
    return device_hostname

def extract_zip(zip_path, extract_to=None):
    # If no extraction path is provided, extract to the same directory as the ZIP file
    if extract_to is None:
        extract_to = os.path.dirname(os.path.abspath(zip_path))

    # Extract the files
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
        
    logger.info(f"Extracted ZIP archive to {extract_to}")

#TODO should just return a unique name
def create_unique_folder(base_path: str, prefix: str) -> str:
    """
    Creates a unique timestamped folder and returns its path.
    """
    # Generate unique folder name with timestamp
    timestamp = datetime.now().strftime("%y%m%d_%H%M")
    folder_name = f"{prefix}_{timestamp}"
    folder_path = os.path.join(base_path, folder_name)
    
    # Create the folder
    os.makedirs(folder_path, exist_ok=True)
    logger.info(f"Folder ready: {folder_path}")
    
    return folder_path

def get_newest_file(directory: str) -> str:
    """Returns the filename (as a string) of the newest file in the directory"""
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
   
    # Check if we found any valid files
    if newest_file is None:
        raise FileNotFoundError(f"No valid timestamped files found in {directory}")
        
    return newest_file

# setup logging
# level alternatives: CRITICAL, ERROR, WARNING, INFO, DEBUG
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# logger level for this module
logger.setLevel(logging.DEBUG)

# logging level for other modules 
logging_level = logging.ERROR

# set paramiko logging level
logging.getLogger("paramiko").setLevel(logging_level)



cleanup_files()

#hej = 0
#if hej == 1:
start_time_stamp_1 = time.perf_counter()
#logger.info("=== Step 1/7: Scanning network ===")
project = "test.nprj"
run_scan(project, "Ethernet 2")
run_backup(project, "169.254.1.1/16")
end_time_stamp_1 = time.perf_counter() #Scan network




start_time_stamp_2 = time.perf_counter() #Creating folder and extracting 
unique_folder = create_unique_folder("./topologies", "project")
extract_zip(project, f"{unique_folder}")
#print(f"Extracted project to {unique_folder}")
logger.info("=== Step 2/7: Parsing device information ===")
#unique_folder = "topologies/project_250416_1708"
unique_folder_without_top = unique_folder.split("/")[1]
logger.debug(f"unique_folder_without_top: {unique_folder_without_top}")
logger.debug(f"unique_folder: {unique_folder}")

end_time_stamp_2 = time.perf_counter() #Creating folder and extracting 


input("Press enter when devices are ready")


start_time_stamp_3 = time.perf_counter() #XML parsing & validation
# list to store devices
device_list: list[Device] = []
xml = xml_info(f"{unique_folder}\Project.xml")
xml.findDevices()
devices_dict = xml.device_list
devices_dict["cloud"] = {"name": "cloud", "id": "cloud", "family": "cloud", "ports": {"virbr0": {}}}

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
        logger.error(f"Error creating device {device_id}: {e}")
    finally:
        # Put ports back in device_data for future reference
        device_data["ports"] = ports_data

# Print device details
if logging_level == logging.DEBUG:
    for device in device_list:
        logger.debug(f"Device Details for: {device.name}")
        for attr, value in device.__dict__.items():
            if attr != "ports" and attr != "vlans":  # Handle port and separately
                logger.debug(f"{attr}: {value}")
        
        logger.debug("VLANs:")
        for vlan_id, vlan in device.vlans.items():
            for vlan_attr, vlan_value in vlan.__dict__.items():
                logger.debug(f"    {vlan_attr}: {vlan_value}")
end_time_stamp_3 = time.perf_counter() #XML parsing & validation




logger.info("=== Step 3/7: Building GNS3 topology ===")



start_time_stamp_4 = time.perf_counter() #Checking existing project, delete if it exists
api_client = GNS3ApiClient()

# set logger level in api_client
# logger level levels: CRITICAL, ERROR, WARNING, INFO, DEBUG
api_client.logger.setLevel(logging_level)

projects = api_client.get_projects()
logger.info(f"Connection successful! Found {len(projects)} projects.")

for dict in projects:
    if dict["name"] == "auto_1":
        id = dict["project_id"]
        api_client.delete_project(id)
        logger.info("Deleted project auto_1")
end_time_stamp_4 = time.perf_counter() #Checking existing project, delete if it exists





logger.info("Building network topology in GNS3...")



start_time_stamp_5 = time.perf_counter() #Building topology
# Create or get project and build devices
topology_builder = TopologyBuilder()

# List available templates to help with configuration
#topology_builder.list_available_templates()

# set logger level in topology_builder
# logger level levels: CRITICAL, ERROR, WARNING, INFO, DEBUG
topology_builder.logger.setLevel(logging_level)

# BUILD DEVICES
try:
    node_mapping = topology_builder.build_topology(device_list)
    
    logger.info(f"Successfully created topology with {len(node_mapping)} devices")
    
    # Save node mapping for link creation (secondary goal)
    with open("node_mapping.json", "w") as f:
        json.dump(node_mapping, f, indent=2)
        
except Exception as e:
    logger.error(f"Error building topology: {str(e)}")
end_time_stamp_5 = time.perf_counter() #Building topology





logger.info("=== Step 4/7: Creating links between devices ===")




start_time_stamp_6 = time.perf_counter() #Creating links
# Parse connections from XML
conn = connections(f"{unique_folder}\Project.xml")
conn.getConnections()
connection_data = conn.conn_dict

# Create link builder
link_builder = LinkBuilder(api_client=topology_builder.api_client)

# set logger level in link_builder
# logger level levels: CRITICAL, ERROR, WARNING, INFO, DEBUG
link_builder.logger.setLevel(logging_level)

try:
    # Get project ID (reuse the same project)
    project_id = topology_builder.create_or_get_project()
    
    # Build links
    links = link_builder.build_links(project_id, connection_data, node_mapping)
    
    logger.info(f"Successfully created {len(links)} links")
    
except Exception as e:
    logger.error(f"Error building links: {str(e)}")
end_time_stamp_6 = time.perf_counter() #Creating links




logger.info("=== Step 5/7: Transferring configuration files ===")




start_time_stamp_7 = time.perf_counter() #Connecting to server
ssh = paramiko.SSHClient()
ssh.load_system_host_keys()
try:
    ssh.connect(hostname='10.2.100.235', username='it')
    logger.info("Successfully connected to SSH server")
except Exception as e:
    logger.error(f"Failed to connect to SSH server: {str(e)}")
end_time_stamp_7 = time.perf_counter() #Connecting to server




logger.debug(f"unique_folder: {unique_folder}")




start_time_stamp_8 = time.perf_counter() #Transfering files
transfer_file(ssh, unique_folder)
end_time_stamp_8 = time.perf_counter() #Transfering files


logger.info("=== Step 6/7: Starting devices ===")



start_time_stamp_9 = time.perf_counter()#Start nodes, validating ping
api_client.start_nodes(project_id)
while True: 
    stdin, stdout, stderr = ssh.exec_command(f"ping -c 1 {get_hostname(device_list[0])}")
    response = stdout.read().decode()
    logger.debug(f"Response: {response}")
    if "1 packets transmitted, 1 received" in response:
        break
end_time_stamp_9 = time.perf_counter()#Start nodes, validating

#input("Press enter when devices are ready")

logger.info("Started all nodes in the project")

logger.info("=== Step 7/7: Configuring devices ===")

start_time_stamp_10 = time.perf_counter()
for device in device_list:
    if device.name != "cloud":
        set_config(unique_folder_without_top , device, ssh) 
end_time_stamp_10 = time.perf_counter()

logger.info("=== Script execution completed successfully ===")

#ssh.close()

logger.info(f"scanning the network took: {end_time_stamp_1 - start_time_stamp_1:.2f} seconds")
logger.info(f"Creating unique folder and unzipping: {end_time_stamp_2 - start_time_stamp_2:.2f} seconds")
logger.info(f"Parsing XML and validating: {end_time_stamp_3 - start_time_stamp_3:.2f} seconds")
logger.info(f"Checking existing project and deleting if it exists: {end_time_stamp_4 - start_time_stamp_4:.2f} seconds")
logger.info(f"Building topology took: {end_time_stamp_5 - start_time_stamp_5:.2f} seconds")
logger.info(f"Creating links took: {end_time_stamp_6 - start_time_stamp_6:.2f} seconds")
logger.info(f"Connecting to server took: {end_time_stamp_7 - start_time_stamp_7:.2f} seconds")
logger.info(f"Transferring files took: {end_time_stamp_8 - start_time_stamp_8:.2f} seconds")
logger.info(f"Starting devices took: {end_time_stamp_9 - start_time_stamp_9:.2f} seconds")
logger.info(f"Setting configuration took: {end_time_stamp_10 - start_time_stamp_10:.2f} seconds")

time_to_start_nodes = end_time_stamp_9 - start_time_stamp_9

logger.info(f"Run time was: {end_time_stamp_10 - start_time_stamp_1 - time_to_start_nodes:.2f} seconds")
logger.info(f"Total time was: {end_time_stamp_10 - start_time_stamp_1:.2f} seconds")


logger.info("=== Step 8/7: scan GNS3 network ===")
stdin, stdout, stderr = ssh.exec_command(f"./publish/weconfig discover --adapterNameOrId virbr0 \
                 --useMdns --useIpConfig -p ./output.nprj")
output = stdout.read()
error = stderr.read()

#Backup GNS3 network -> Paramiko to start backup on server 
logger.info("=== Step 9/7: Backup GNS3 network ===")
stdin, stdout, stderr = ssh.exec_command(f"./publish/weconfig backup -s 169.254.0.0/16 -p ./output.nprj")
output = stdout.read()
error = stderr.read()

logger.info("===== Step 10/7: Transfering backup file ====")
#Send backup files to windows pc -> scp to send files to pc 
get_file(ssh, '~/output.nprj')

logger.info("=== Step 11/7: Extracting backup file ===")
#Extract nprj file
extract_zip("output.nprj", "./gns3_backups")

#Use python version of restore.sh to restore backup on physical devices. 