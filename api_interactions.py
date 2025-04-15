import requests
import yaml
import logging
from typing import Dict, Any, Optional, List, Tuple
import json

class GNS3ApiError(Exception):
    """Custom exception for GNS3 API errors."""
    pass

class GNS3ApiClient:
    """Client for interacting with the GNS3 API."""

    def __init__(self, config_path: str = "config.yaml"):
        """Initialize the GNS3 API client with configuration."""
        self.config = self._load_config(config_path)
        self.base_url = f"{self.config['gns3_server']['protocol']}://{self.config['gns3_server']['host']}:{self.config['gns3_server']['port']}/v2"
        self.session = requests.Session()
        
        # Set up authentication if configured
        if 'username' in self.config['gns3_server'] and 'password' in self.config['gns3_server']:
            self.session.auth = (self.config['gns3_server']['username'], self.config['gns3_server']['password'])
            
        # Set up logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from a YAML file."""
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file)
        except Exception as e:
            raise GNS3ApiError(f"Failed to load configuration: {str(e)}")
    
    def _request(self, method: str, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a request to the GNS3 API."""
        url = f"{self.base_url}/{endpoint}"
        self.logger.debug(f"Making {method} request to {url}")
    
        try:
            if method.lower() == 'get':
                response = self.session.get(url)
            elif method.lower() == 'post':
                # Print the entire POST request details instead of just logging the data
                print(f"POST Request to {url}")
                print(f"Headers: {self.session.headers}")
                print(f"Body: {json.dumps(data, indent=2)}")
                response = self.session.post(url, json=data)
            elif method.lower() == 'put':
                response = self.session.put(url, json=data)
            elif method.lower() == 'delete':
                response = self.session.delete(url)
            else:
                raise GNS3ApiError(f"Unsupported HTTP method: {method}")
    
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request failed: {str(e)}")
            raise GNS3ApiError(f"API request failed: {str(e)}")
    
    def get_projects(self) -> List[Dict[str, Any]]:
        """Get all projects."""
        return self._request('get', 'projects')
    
    def create_project(self, name: str) -> Dict[str, Any]:
        """Create a new project."""
        data = {"name": name}
        return self._request('post', 'projects', data)
    
    def get_project(self, project_id: str) -> Dict[str, Any]:
        """Get project details by ID."""
        return self._request('get', f'projects/{project_id}')
    
    def delete_project(self, project_id: str) -> Dict[str, Any]:
        """Delete a project by ID."""
        return self._request('delete', f'projects/{project_id}')
    
    def create_node(self, project_id: str, name: str, template_id: str, 
                   position: Tuple[float, float]) -> Dict[str, Any]:
        """Create a new node in the project."""
        data = {
            "x": position[0],
            "y": position[1],
            "name": name
        }
        return self._request('post', f'projects/{project_id}/templates/{template_id}', data)
    
    def create_cloud(self, project_id: str, name: str, template_id: str, 
                   position: Tuple[float, float]) -> Dict[str, Any]:
        """Create a new node in the project."""
        data = {
            "x": position[0],
            "y": position[1],
            "compute_id": "local",
            "name": name
        }
        return self._request('post', f'projects/{project_id}/templates/{template_id}', data)
    
    def create_default_node(self, project_id: str, name: str, position: Tuple[float, float]) -> Dict[str, Any]:
        """Create a new node using the default template."""
        return self.create_node(project_id, name, '0da18376-a083-4284-9610-e1f3db7d9344', position)
    
    def get_nodes(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all nodes in a project."""
        return self._request('get', f'projects/{project_id}/nodes')
    
    def get_node(self, project_id: str, node_id: str) -> Dict[str, Any]:
        """Get node details by ID."""
        return self._request('get', f'projects/{project_id}/nodes/{node_id}')
    
    def delete_node(self, project_id: str, node_id: str) -> Dict[str, Any]:
        """Delete a node by ID."""
        return self._request('delete', f'projects/{project_id}/nodes/{node_id}')
    
    def get_templates(self) -> List[Dict[str, Any]]:
        """Get all available templates/appliances."""
        return self._request('get', 'templates')
    
    def create_link(self, project_id: str, source_node_id: str, source_port: int, 
                    target_node_id: str, target_port: int) -> Dict[str, Any]:
        """Create a link between two nodes in a project."""
        data = {
            'nodes': [
                {
                    'node_id': source_node_id,
                    'adapter_number': source_port, # Adjust for 0-based indexing
                    'port_number': 0
                },
                {
                    'node_id': target_node_id,
                    'adapter_number': target_port, # Adjust for 0-based indexing
                    'port_number': 0
                }
            ]
        }
        return self._request('post', f'projects/{project_id}/links', data)
    
    def create_cloud_link(self, project_id: str, source_node_id: str,
                          source_port: int, target_node_id: str,
                          target_port: int) -> Dict[str, Any]:
        """Create a link between a node and cloud."""
 
        data = {
            'nodes': [
                {
                    'node_id': source_node_id,
                    'adapter_number': 0, # Adjust for 0-based indexing
                    'port_number': 1
                },
                {
                    'node_id': target_node_id,
                    'adapter_number': target_port - 1, # Adjust for 0-based indexing
                    'port_number': 0
                }
            ],
            'filters': {},
            'link_style': {},
            'suspend': False
        }
 
        return self._request('post', f'projects/{project_id}/links', data)
    
 
    def update_node(self, project_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
         """Update node"""
         return self._request('post', f'projects/{project_id}/links', data)
    
    def update_cloud(self, project_id: str, node_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Update cloud node"""
        return self._request('put', f'projects/{project_id}/nodes/{node_id}', data)
    