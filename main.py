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
from win_restore import restore_backup

import randomname   


# On Oskar's computer, the path to the new WeConfig is:
# ~\AppData\Local\WeConfig-dev-cli\current\WeConfig.exe

# On the server, the path to the new WeConfig is the same

def cleanup_all_files():
    logger.debug("=== cleaning up files ===")
    cleanup_files("./topologies", "./test.nprj")
    logger.debug("deleting files in topologies")
    cleanup_files("./gns3_backups", "./output.nprj")
    logger.debug("deleting files in gns3_backups")
    cleanup_files_vm()
    logger.debug("deleting files in vm")

def find_matching_devices_by_mac(list1, list2):
    """
    Find devices with matching base_mac values between two lists.
    Returns a list of tuples with matching devices (device_from_list1, device_from_list2).
    """
    # Create dictionary with base_mac as key for O(1) lookups
    mac_to_device = {}
    for device in list1:
        # Only add devices with valid MAC addresses
        if device.base_mac is not None and device.base_mac != "":
            mac_to_device[device.base_mac] = device
    
    # Find matches in list2
    matches = []
    for device2 in list2:
        # First check if device2 has a valid MAC address
        if device2.base_mac is not None and device2.base_mac != "":
            # Then check if that MAC address exists in our lookup dictionary
            if device2.base_mac in mac_to_device:
                # We found a match - add the pair to our results
                device1 = mac_to_device[device2.base_mac]
                matches.append((device1, device2))
    
    return matches

def cleanup_files(topologies_path, test_file):
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
        if os.path.exists(test_file):
            try:
                os.remove(test_file)
                logger.debug(f"Removed {test_file}")
            except Exception as e:
                logger.error(f"Failed to delete {test_file}: {str(e)}")
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        
def cleanup_files_vm():
    ssh_vm = paramiko.SSHClient()
    ssh_vm.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_vm.load_system_host_keys()
    
    try:
        logger.debug(f"Connecting to GNS3-server:")
        ssh_vm.connect(hostname='10.2.100.235', username='it')
    except Exception as e:
        logger.error(f"Failed to connect to SSH server: {str(e)}")
        return
    
    ssh_vm.exec_command("rm ~/output.nprj")
    logger.debug("Removed ~/output.nprj")
    ssh_vm.exec_command("rm -rf ~/NDT/project_files/*")
    logger.debug("Removed all files in ~/NDT/project_files/")
    
    ssh_vm.close()
     
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
    """Transfer a folder to the remote server using SCP."""
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

def extract_zip(zip_path, extract_to):
    """
    Extracts a ZIP file to the specified directory.
    """
    
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

def create_folder(folder_path, name):
    folder_name = name
    folder_path = os.path.join(folder_path, folder_name)
    os.makedirs(folder_path, exist_ok=True)
    logger.debug(f'Created fodler {folder_path}')
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

def change_hostname(hostname, new_name):
    ssh1 = paramiko.SSHClient()
    ssh1.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh1.load_system_host_keys()
    
    try:
        logger.debug(f"Connecting to GNS3-server:")
        ssh1.connect(hostname='10.2.100.235', username='it')
        logger.debug("Successfully connected to SSH server")
        
        # Create an interactive shell session
        channel = ssh1.invoke_shell()
        channel.settimeout(None)  # No timeout
        
        # Function to wait for output continuously with optional timeout
        def wait_and_log_output(check_for=None, respond_with=None, timeout=None):
            """
            Wait for output and log it.
            If timeout is None, wait indefinitely until output is received.
            """
            buffer = ""
            start_time = time.time()
            
            while True:
                # Check timeout only if specified
                if timeout is not None and (time.time() - start_time > timeout):
                    logger.debug(f"Timeout after {timeout} seconds")
                    return buffer
                
                # Small sleep to avoid CPU spinning
                time.sleep(0.5)
                
                if channel.recv_ready():
                    chunk = channel.recv(8192).decode('utf-8', errors='ignore')
                    if chunk:
                        buffer += chunk
                        logger.debug(f"Received output: {chunk}")
                        
                        # If we're checking for specific text and it's found
                        if check_for and check_for in buffer:
                            logger.debug(f"Found expected text: '{check_for}'")
                            if respond_with:
                                logger.debug(f"Sending response: '{respond_with}'")
                                channel.send(respond_with)
                            return buffer
                
                # If we're not checking for specific text, return once we have some output
                # and there's no more output ready for a moment
                if not check_for and buffer and not channel.recv_ready():
                    # Small additional wait to ensure no more immediate output
                    time.sleep(1)
                    if not channel.recv_ready():
                        return buffer
        
        # Clear initial output
        initial_output = wait_and_log_output()
        logger.debug(f"Initial SSH server output: {initial_output}")
        
        # Flag to track if we need to retry due to host key change
        retry_needed = False
        
        # Try SSH connection (with potential retry)
        for attempt in range(2):  # At most 2 attempts
            if attempt > 0:
                logger.debug(f"Retry attempt {attempt} for SSH connection")
            
            # Send the SSH command
            logger.debug(f"Starting SSH connection to {hostname}")
            channel.send(f"ssh admin@{hostname}\n")
            
            # Wait for first response - NO TIMEOUT here
            ssh_response = wait_and_log_output()
            
            # Check for host key verification failure
            if "WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED" in ssh_response:
                logger.debug("Host key has changed. Removing old key and will retry.")
                
                # Extract the command to remove the key from the message
                key_remove_cmd = None
                for line in ssh_response.splitlines():
                    if "ssh-keygen -f" in line and "-R" in line:
                        key_remove_cmd = line.strip()
                        break
                
                if key_remove_cmd:
                    logger.debug(f"Running command: {key_remove_cmd}")
                    channel.send(f"{key_remove_cmd}\n")
                    
                    # Wait for command completion - NO TIMEOUT
                    key_remove_output = wait_and_log_output()
                    logger.debug(f"Key removal output: {key_remove_output}")
                    
                    # We need to retry the SSH connection
                    retry_needed = True
                    continue
                else:
                    logger.error("Could not find key removal command in error message")
                    return False
            
            # No key error or already retried, proceed with normal connection
            break
        
        # Continue with normal connection process
        output = ssh_response
        
        # Check for different prompts and respond accordingly
        while True:
            if "Are you sure you want to continue connecting" in output:
                logger.debug("Host key verification prompt detected, sending 'yes'")
                channel.send("yes\n")
                
                # Wait for password prompt after sending yes - NO TIMEOUT
                passwd_output = wait_and_log_output()
                output += passwd_output
            
            if "password:" in output:
                logger.debug("Password prompt detected, sending password")
                channel.send("admin\n")
                break
            
            # If we haven't seen either prompt yet, wait for more output - NO TIMEOUT
            logger.debug("Waiting for verification or password prompt...")
            more_output = wait_and_log_output()
            output += more_output
        
        # Wait for login to complete (command prompt) - NO TIMEOUT
        login_output = ""
        while True:
            new_output = wait_and_log_output()
            login_output += new_output
            
            if ":/#>" in login_output:
                logger.debug("Successfully logged in, prompt detected")
                break
            
            # If we don't see the prompt yet, continue waiting
            logger.debug("Still waiting for login prompt...")
        
        # Send hostname change command
        logger.debug(f"Sending command to change hostname to {new_name}")
        hostname_command = f"config hostname {new_name} le\n"
        channel.send(hostname_command)
        
        time.sleep(10)
        
        save_command = "copy run start\n"
        logger.debug(f"Sending command to save configuration: {save_command}")
        channel.send(save_command)
        
        time.sleep(10)
        
        # Wait for command completion - reasonable timeout ok here (30 sec)
        #cmd_output = wait_and_log_output(timeout=30)
        #logger.debug(f"Output after hostname change: {cmd_output}")
        
        ssh1.close()
        
    except Exception as e:
        logger.error(f"Failed in change_hostname: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        if 'ssh1' in locals() and ssh1:
            ssh1.close()
        return False
    
def random_new_name():
    """Generate a random hostname using the randomname library."""
    name = randomname.generate(('names/codenames/intel'))
    return name


# setup logging
# level alternatives: CRITICAL, ERROR, WARNING, INFO, DEBUG
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger(__name__)

# logger level for this module
logger.setLevel(logging.DEBUG)

# logging level for other modules 
logging_level = logging.ERROR

# set paramiko logging level
logging.getLogger("paramiko").setLevel(logging_level)

cleanup_all_files()

start_time_stamp_1 = time.perf_counter()
logger.info("=== Step 1/7: Scanning network ===")
project = "test.nprj"
run_scan(project, "Ethernet 5") # ensure this is correct adapter name
run_backup(project, "169.254.1.1/16")
end_time_stamp_1 = time.perf_counter() #Scan network

# for debugging purposes
project = "test.nprj"

start_time_stamp_2 = time.perf_counter() #Creating folder and extracting 
unique_folder = create_unique_folder("./topologies", "project")
logger.debug(f"extracting to: {unique_folder}")
extract_zip(project, unique_folder)
print(f"Extracted project to {unique_folder}")
logger.info("=== Step 2/7: Parsing device information ===")
unique_folder_without_top = unique_folder.split("\\")[1]
logger.debug(f"unique_folder_without_top: {unique_folder_without_top}")
logger.debug(f"unique_folder: {unique_folder}")
end_time_stamp_2 = time.perf_counter() #Creating folder and extracting 

start_time_stamp_3 = time.perf_counter() #XML parsing & validation
# list to store devices
device_list: list[Device] = []
xml_path = os.path.join(unique_folder, "Project.xml")
xml = xml_info(xml_path)
xml.findDevices()
devices_dict = xml.device_list
devices_dict["cloud"] = {"name": "cloud", 
                         "id": "cloud", 
                         "family": "cloud", 
                         "ports": {"virbr0": {}}}

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





#logger.info("Building network topology in GNS3...")



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
    
    #logger.info(f"Successfully created topology with {len(node_mapping)} devices")
    
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
logger.info("Transferring files to server...")
logger.debug(f"Transferring folder {unique_folder} via SCP")
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

logger.info("=== Step 8/7: Printing timing info ===")
# Standard format logging for timing information
logger.info(f"scanning_physical_network:{end_time_stamp_1 - start_time_stamp_1:.4f}")
logger.info(f"creating_folder_and_unzipping:{end_time_stamp_2 - start_time_stamp_2:.4f}")
logger.info(f"parsing_xml_and_validating:{end_time_stamp_3 - start_time_stamp_3:.4f}")
logger.info(f"checking_existing_project:{end_time_stamp_4 - start_time_stamp_4:.4f}")
logger.info(f"building_topology:{end_time_stamp_5 - start_time_stamp_5:.4f}")
logger.info(f"creating_links:{end_time_stamp_6 - start_time_stamp_6:.4f}")
logger.info(f"connecting_to_server:{end_time_stamp_7 - start_time_stamp_7:.4f}")
logger.info(f"transferring_files:{end_time_stamp_8 - start_time_stamp_8:.4f}")
logger.info(f"starting_devices:{end_time_stamp_9 - start_time_stamp_9:.4f}")
logger.info(f"setting_configuration:{end_time_stamp_10 - start_time_stamp_10:.4f}")

time_to_start_nodes = end_time_stamp_9 - start_time_stamp_9
#run_time = end_time_stamp_10 - start_time_stamp_1 - time_to_start_nodes
#logger.info(f"run_time:{run_time:.4f}")
#logger.info(f"physical_to_ndt_delay:{end_time_stamp_10 - start_time_stamp_1:.4f}")
physical_to_ndt_delay = end_time_stamp_10 - start_time_stamp_1 - time_to_start_nodes
logger.info(f"physical_to_ndt_delay:{physical_to_ndt_delay:.4f}")

#input("Press enter to continue")
logger.info("Sleeping 40s")
time.sleep(40)
#TODO wait for textoutput from device before proceeding

logger.info("=== Step 8/7: Changing hostnames ===")
name = random_new_name()
logger.debug(f"Name: {name}")
name2 = random_new_name()
logger.debug(f"Name2: {name2}")
while name2 == name:
    logger.debug(f"Name2: {name2} is the same as name: {name}")
    name2 = random_new_name()
    logger.debug(f"name2: is now {name2}")
logger.debug(f"Name2: {name2} is different from name: {name}")

change_hostname(f"{device_list[1].name}.local", name)

change_hostname(f"{device_list[0].name}.local", name2)

logger.info("Sleeping 20s")
time.sleep(20)
#TODO wait for textoutput from device before proceeding

#input("Press enter to continue")

logger.info("=== Step 8/7: scan GNS3 network ===")
start_time_stamp_11 = time.perf_counter()
stdin, stdout, stderr = ssh.exec_command(f"./publish/weconfig discover --adapterNameOrId virbr0 \
                 --useMdns --useIpConfig -p ./output.nprj")
output = stdout.read()
error = stderr.read()
end_time_stamp_11 = time.perf_counter()

#Backup GNS3 network -> Paramiko to start backup on server 
logger.info("=== Step 9/7: Backup GNS3 network ===")
start_time_stamp_12 = time.perf_counter()
stdin, stdout, stderr = ssh.exec_command(f"./publish/weconfig backup -s 169.254.0.0/16 -p ./output.nprj")
output = stdout.read()
error = stderr.read()
end_time_stamp_12 = time.perf_counter()

logger.info("===== Step 10/7: Transfering backup file ====")
start_time_stamp_13 = time.perf_counter()
#Send backup files to windows pc -> scp to send files to pc 
get_file(ssh, '~/output.nprj')
end_time_stamp_13 = time.perf_counter()

logger.info("=== Step 11/7: Extracting backup file ===")
#Extract nprj file
start_time_stamp_14 = time.perf_counter()
unique_folder_without_top = unique_folder.split('\\')[1]
logger.debug(f"Unique folder without top = {unique_folder_without_top}")
gns3_folder = create_folder("./gns3_backups", unique_folder_without_top)
extract_zip("output.nprj", gns3_folder)
end_time_stamp_14 = time.perf_counter()
#ssh.close()

logger.info("=== Step 11/7: Parsing XML and validating keys ===")
start_time_stamp_15 = time.perf_counter()
device_list_gns3: list[Device] = []
xml_gns3_path = os.path.join(gns3_folder, "Project.xml")
xml_gns3 = xml_info(xml_gns3_path)
xml_gns3.findDevices()

devices_dict = xml_gns3.device_list

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
        device_list_gns3.append(device)
        
    except Exception as e:
        logger.error(f"Error creating device {device_id}: {e}")
    finally:
        # Put ports back in device_data for future reference
        device_data["ports"] = ports_data
end_time_stamp_15 = time.perf_counter()


logger.info("=== Step 11/7: Matching gns3 and real world devices ===")
start_time_stamp_16 = time.perf_counter() #Find matches 
matches = find_matching_devices_by_mac(device_list, device_list_gns3)
logger.debug(f"Matches: {matches}")
end_time_stamp_16 = time.perf_counter()


logger.info("=== Step 11/7: Applying config ===")
start_time_stamp_17 = time.perf_counter() #Apply config
for match in matches:
    logger.debug(f"Match: {match[0].name} - {match[1].name}")
    logger.debug(f"Match: {match[0].base_mac} - {match[1].base_mac}")
    logger.debug(f"Match: {match[0].ip_address} - {gns3_folder}/{match[1].id}.json")
    ip = f"https://{match[0].ip_address}"
    path = f"{gns3_folder}/{match[1].id}.json"
    file_to_restore = get_newest_file(f"{gns3_folder}\\Configuration Backups\\{match[1].id}")
    logger.debug(f"File to restore: {file_to_restore}")
    path_to_conf = os.path.join(gns3_folder, "Configuration Backups", match[1].id, file_to_restore)
    logger.debug(f"Path to conf: {path_to_conf}")
    restore_backup("admin", "admin", ip,  path_to_conf)
end_time_stamp_17 = time.perf_counter()

# Standard format logging for timing information - second phase
logger.info(f"scanning_virtual_network:{end_time_stamp_11 - start_time_stamp_11:.4f}")
logger.info(f"backup_ndt:{end_time_stamp_12 - start_time_stamp_12:.4f}")
logger.info(f"transferring_backup_file:{end_time_stamp_13 - start_time_stamp_13:.4f}")
logger.info(f"extracting_backup_file:{end_time_stamp_14 - start_time_stamp_14:.4f}")
logger.info(f"parsing_ndt_xml:{end_time_stamp_15 - start_time_stamp_15:.4f}")
logger.info(f"matching_devices:{end_time_stamp_16 - start_time_stamp_16:.4f}")
logger.info(f"applying_config:{end_time_stamp_17 - start_time_stamp_17:.4f}")

ndt_to_physical_delay = end_time_stamp_17 - start_time_stamp_11
logger.info(f"ndt_to_physical_delay:{ndt_to_physical_delay:.4f}")

round_trip_time = physical_to_ndt_delay + (end_time_stamp_17 - start_time_stamp_11)
logger.info(f"round_trip_time:{round_trip_time:.4f}")

#Use python version of restore.sh to restore backup on physical devices.  

#for device, gns3_device in device_list_1, device_list_2:
    #
    #base_mac device_list1
    #find hostname 
    

cleanup_all_files()