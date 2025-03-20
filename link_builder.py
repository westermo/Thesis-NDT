from typing import Dict, Any, List
from api_interactions import GNS3ApiClient, GNS3ApiError
import logging
import yaml

class LinkBuilder:
    """Builds links between devices in GNS3 topologies."""
    
    def __init__(self, api_client=None, config_path: str = "config.yaml"):
        """Initialize the link builder."""
        self.api_client = api_client or GNS3ApiClient(config_path)
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
    
    def build_links(self, project_id: str, connections: Dict[str, Any], node_mapping: Dict[str, str]) -> List[Dict[str, Any]]:
        """Build links between nodes based on connection data."""
        links_created = []
        
        for conn_id, conn_data in connections.items():
            try:
                # Extract source and target device IDs
                source_device_id = conn_data.get('SourceDeviceId')
                target_device_id = conn_data.get('TargetDeviceId')
                
                # Skip if missing required data
                if not source_device_id or not target_device_id:
                    self.logger.warning(f"Skipping connection {conn_id}: Missing device IDs")
                    continue
                
                # Get port numbers
                source_port = conn_data.get('source_device_port')
                target_port = conn_data.get('target_device_port')
                
                # Skip if missing port info
                if source_port is None or target_port is None:
                    self.logger.warning(f"Skipping connection {conn_id}: Missing port information")
                    continue
                
                # Get GNS3 node IDs from mapping
                source_node_id = node_mapping.get(source_device_id)
                target_node_id = node_mapping.get(target_device_id)
                
                # Skip if node mapping not found
                if not source_node_id or not target_node_id:
                    self.logger.warning(f"Skipping connection {conn_id}: Device not found in node mapping")
                    continue
                
                # Create the link using the API client
                link = self.api_client.create_link(
                    project_id, 
                    source_node_id, 
                    source_port, 
                    target_node_id, 
                    target_port
                )
                
                links_created.append({
                    'connection_id': conn_id,
                    'link_id': link.get('link_id'),
                    'source_device': source_device_id,
                    'target_device': target_device_id
                })
                
                self.logger.info(f"Created link for connection {conn_id}")
                
            except Exception as e:
                self.logger.error(f"Failed to create link for connection {conn_id}: {str(e)}")
                
        return links_created