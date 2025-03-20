from typing import Dict, Any, List
from data_model import Device
from api_interactions import GNS3ApiClient, GNS3ApiError
import logging
import yaml

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
        default_template_id = self.config['template']['default_appliance_id']
        
        # Get scaling factors from config with defaults
        # get(primary, secondary) -> primary or secondary if primary is None
        position_scale = self.config['project'].get('position_scale', {})
        scale_x = position_scale.get('x', 1)
        scale_y = position_scale.get('y', 1)
        
        node_mapping = {}  # Map device IDs to GNS3 node IDs
        
        for device in device_list:
            try:
                # Use device position or default to (0,0)
                position = device.position if device.position else (0, 0)
                # Scale position using separate factors for x and y
                position = (int(position[0] * scale_x), int(position[1] * scale_y))
                
                # Create node in GNS3
                node = self.api_client.create_node(
                    project_id=project_id,
                    name=device.name or f"{device.family}-{device.model}",
                    template_id=default_template_id,
                    position=position
                )
                
                # Store mapping
                node_mapping[device.id] = node['node_id']
                self.logger.info(f"Created node for device: {device.name}")
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