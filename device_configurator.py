# Updated device_configurator.py
import os
import subprocess
import logging
import json
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

class ConfigurationError(Exception):
    """Custom exception for configuration errors."""
    pass

class DeviceConfigurator:
    """Manages device configurations and setup."""
    
    def __init__(self, topology_path: str, node_mapping: Dict[str, str], api_client=None):
        """Initialize the configuration manager."""
        self.topology_path = Path(topology_path)
        self.backup_path = self.topology_path / "Configuration Backups"
        self.node_mapping = node_mapping
        self.api_client = api_client
        self.logger = logging.getLogger(__name__)
        
        # Validate backup path exists
        if not self.backup_path.exists():
            self.logger.error(f"Backup path does not exist: {self.backup_path}")
            raise ConfigurationError(f"Backup path does not exist: {self.backup_path}")
    
    def scan_backups(self) -> Dict[str, List[Path]]:
        """Scan backup folders and organize by device ID."""
        device_backups = {}
        
        try:
            # Iterate through device folders in backup directory
            for device_folder in self.backup_path.iterdir():
                if device_folder.is_dir():
                    device_id = device_folder.name
                    device_backups[device_id] = []
                    
                    # Find all JSON configuration files
                    for config_file in device_folder.glob("*.json"):
                        device_backups[device_id].append(config_file)
                    
                    # Sort by date (assuming format: YYYY-MM-DDTHH_MM_SSZ.json)
                    device_backups[device_id].sort(reverse=True)
                    
            return device_backups
        except Exception as e:
            self.logger.error(f"Error scanning backup folders: {str(e)}")
            raise ConfigurationError(f"Error scanning backup folders: {str(e)}")
    
    def get_latest_config(self, device_id: str) -> Optional[Path]:
        """Get the latest configuration file for a device."""
        device_backups = self.scan_backups()
        if device_id in device_backups and device_backups[device_id]:
            return device_backups[device_id][0]
        return None
    
    def extract_hostnames_from_configs(self) -> Dict[str, str]:
        """Extract hostnames from configuration files."""
        hostnames = {}
        device_backups = self.scan_backups()
        
        for device_id, configs in device_backups.items():
            if configs:
                try:
                    # Read the latest config file
                    with open(configs[0], 'r') as f:
                        config_data = json.load(f)
                    
                    # Extract hostname from the config
                    if 'system' in config_data and 'hostname' in config_data['system']:
                        hostnames[device_id] = config_data['system']['hostname']
                except Exception as e:
                    self.logger.error(f"Error extracting hostname for device {device_id}: {str(e)}")
        
        return hostnames
    
    def apply_configuration(self, device_id: str, hostname: str, config_file: Path, 
                           username: str = "admin", password: str = "admin") -> bool:
        """Apply a configuration to a device."""
        try:
            # Construct address from hostname (use hostname.local)
            address = f"http://{hostname}.local"
            
            # Build restore command using subprocess
            cmd = [
                "bash", "restore.sh",
                username,
                password,
                address,
                str(config_file)
            ]
            
            self.logger.info(f"Applying config to {hostname} from {config_file}")
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                self.logger.error(f"Failed to apply config: {stderr.decode()}")
                return False
                
            self.logger.info(f"Configuration applied successfully to {hostname}")
            return True
        except Exception as e:
            self.logger.error(f"Error applying configuration: {str(e)}")
            return False
    
    def apply_all_configurations(self) -> Dict[str, bool]:
        """Apply configurations to all devices."""
        results = {}
        device_backups = self.scan_backups()
        hostnames = self.extract_hostnames_from_configs()
        
        for device_id, configs in device_backups.items():
            if device_id in self.node_mapping and configs:
                # Get hostname for this device
                if device_id in hostnames:
                    hostname = hostnames[device_id]
                    # Apply latest config
                    success = self.apply_configuration(device_id, hostname, configs[0])
                    results[device_id] = success
                else:
                    self.logger.warning(f"No hostname found for device {device_id}")
        
        return results
    
    def extract_mac_addresses_from_xml(self) -> Dict[str, str]:
        """Extract MAC addresses from project XML file."""
        mac_addresses = {}
        xml_path = self.topology_path / "Project.xml"
        
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()
            namespace = {'ns': 'http://westermo.com/weconfig'}
            
            # Find all Device elements and extract MAC addresses
            for device in root.findall(".//ns:Device", namespace) or root.findall(".//*[@Id]"):
                if 'Id' in device.attrib:
                    device_id = device.attrib['Id']
                    
                    # Find chassis ID/MAC address
                    chassis_id = device.find(".//*[@Type='MacAddress']")
                    if chassis_id is not None and chassis_id.text:
                        mac_addresses[device_id] = chassis_id.text
            
            return mac_addresses
        except Exception as e:
            self.logger.error(f"Error extracting MAC addresses from XML: {str(e)}")
            return {}
    
    def setup_cloud_appliance(self, project_id: str, position: Tuple[float, float] = (0, 0)) -> Optional[str]:
        """Create and set up a cloud appliance."""
        if not self.api_client:
            self.logger.error("API client not available")
            return None
            
        try:
            # Create cloud appliance
            self.logger.info("Creating cloud appliance...")
            cloud_node = self.api_client.create_cloud_appliance(project_id, position)
            cloud_node_id = cloud_node.get('node_id')
            
            if not cloud_node_id:
                self.logger.error("Failed to get cloud node ID")
                return None
            
            # Configure cloud interfaces
            self.logger.info("Configuring cloud interfaces...")
            self.api_client.update_cloud_interfaces(project_id, cloud_node_id)
            
            return cloud_node_id
        except Exception as e:
            self.logger.error(f"Error setting up cloud: {str(e)}")
            return None
    
    def set_mac_addresses(self, project_id: str) -> Dict[str, bool]:
        """Set MAC addresses for all nodes based on XML data."""
        results = {}
        mac_addresses = self.extract_mac_addresses_from_xml()
        
        if not self.api_client:
            self.logger.error("API client not available")
            return results
            
        for device_id, node_id in self.node_mapping.items():
            if device_id in mac_addresses:
                mac_address = mac_addresses[device_id]
                try:
                    self.logger.info(f"Setting MAC address {mac_address} for node {node_id}")
                    self.api_client.set_node_mac_address(project_id, node_id, mac_address)
                    results[device_id] = True
                except Exception as e:
                    self.logger.error(f"Error setting MAC address for node {node_id}: {str(e)}")
                    results[device_id] = False
        
        return results