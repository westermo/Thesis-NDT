from typing import Dict, Any, List
from data_model import Device
from api_interactions import GNS3ApiClient, GNS3ApiError
import logging
import yaml
import random

class TopologyBuilder:
    """Builds GNS3 topologies based on device data."""
    
    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the topology builder."""
        self.api_client = GNS3ApiClient(config_path)
        self.config = self._load_config(config_path)
        self.logger = logging.getLogger(__name__)
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from a YAML file."""
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {str(e)}")
            raise ValueError(f"Failed to load configuration: {str(e)}")
        
    def _get_template_for_device(self, device: Device) -> str:
        """Get the appropriate template ID for a device."""
        # Default template
        default_template = self.config['template']['default_appliance_id']
        
        # Check for model-specific template (highest priority)
        model_templates = self.config['template'].get('model_templates', {})
        if model_templates:
            if device.model in model_templates:
                return model_templates[device.model]
        
        # Check for family-specific template
        family_templates = self.config['template'].get('device_templates', {})
        if family_templates:
            if device.family in family_templates:
                return family_templates[device.family]
        
        # Return default if no match found
        return default_template
    
    def create_or_get_project(self) -> str:
        """Create a new project or get an existing one."""
        project_name = self.config['project']['name']
        
        # Check if project already exists
        projects = self.api_client.get_projects()
        for project in projects:
            if project['name'] == project_name:
                self.logger.info(f"Found existing project: {project_name}")
                return project['project_id']
        
        # Create new project if none exists
        self.logger.info(f"Creating new project: {project_name}")
        project = self.api_client.create_project(project_name)
        return project['project_id']
    
    def build_devices(self, device_list: List[Device], project_id: str) -> Dict[str, str]:
        """Create nodes in GNS3 based on device list."""
        # Get position scaling factors
        position_scale = self.config['project'].get('position_scale', {})
        scale_x = position_scale.get('x', 1)
        scale_y = position_scale.get('y', 1)
        
        node_mapping = {}  # Map device IDs to GNS3 node IDs
        
        for device in device_list:
            try:
                # Get appropriate template for this device
                template_id = self._get_template_for_device(device)
                
                # Use device position or default to (0,0)
                position = device.position if device.position else (random.randint(-100, 100), random.randint(-100, 100)) #TODO add random position generator if no position is given
                # Scale position using separate factors for x and y
                position = (int(position[0] * scale_x), int(position[1] * scale_y))
                
                if device.family == "cloud":
                    self.logger.info(f"Creating cloud node for device: {device.name}")
                    node = self.api_client.create_cloud(
                        project_id=project_id,
                        name=device.name or f"{device.family}-{device.model}",
                        template_id=template_id,
                        position=position
                    )

                    cloud_data_dict = {
                        "properties": {
                            "ports_mapping": [
                                {
                                    "interface": "ens33",
                                    "name": "ens33",
                                    "port_number": 0,
                                    "type": "ethernet"
                                },
                                {
                                    "name": "virbr0",
                                    "port_number": 1,
                                    "type": "ethernet",
                                    "interface": "virbr0"
                                }
                            ]
                        },
                        "node_type": "cloud",
                        "node_id": node['node_id'],
                        "compute_id": "local"
                    }

                    node = self.api_client.update_node(node["project_id"], 
                                                node["node_id"], 
                                                cloud_data_dict)
                else:
                    # Create node in GNS3
                    node = self.api_client.create_node(
                        project_id=project_id,
                        name=device.name or f"{device.family}-{device.model}",
                        template_id=template_id,
                        position=position
                    )

                    base_mac_dict = {
                        "properties": {
                            "base_mac": device.base_mac
                        }
                    }

                    # call set_mac to set the base mac of the node
                    self.api_client.update_node(node["project_id"], 
                                                node["node_id"], 
                                                base_mac_dict)

                # Store mapping
                node_mapping[device.id] = node['node_id']
                self.logger.info(f"Created node for device: {device.name} (using template: {template_id})")
            except GNS3ApiError as e:
                self.logger.error(f"Failed to create node for device {device.name}: {str(e)}")
        
        return node_mapping
    
    def build_topology(self, device_list: List[Device]) -> Dict[str, str]:
        """Build a complete topology with all devices."""
        try:
            # Get or create project
            project_id = self.create_or_get_project()
            
            # Create devices
            node_mapping = self.build_devices(device_list, project_id)
            
            return node_mapping
        except Exception as e:
            self.logger.error(f"Error building topology: {str(e)}")
            raise

    def list_available_templates(self):
        """Print all available templates in GNS3."""
        templates = self.api_client.get_templates()
        print("\nAvailable GNS3 Templates:")
        print("-" * 50)
        for template in templates:
            print(f"Name: {template.get('name')}")
            print(f"ID: {template.get('template_id')}")
            print(f"Type: {template.get('template_type', 'unknown')}")
            print("-" * 50)