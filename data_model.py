from dataclasses import dataclass, field
from typing import Dict, Tuple, Optional, Any

# connection

# topology

# configuration

@dataclass
class Vlan:
    name: Optional[str] = None
    address: Optional[str] = None

@dataclass
class Port:
    name: Optional[str] = None
    id: Optional[Any] = None  # Using Any since it could be str or int
    mac_address: Optional[str] = None
    up: Optional[bool] = None

@dataclass
class Device:
    name: Optional[str] = None
    id: Optional[str] = None
    position: Optional[Tuple[float, float]] = None
    family: Optional[str] = None
    model: Optional[str] = None
    image: Optional[str] = None
    ip_address: Optional[str] = None
    net_mask: Optional[str] = None
    ports: Dict[str, Port] = field(default_factory=dict)
    vlans: Dict[str, Vlan] = field(default_factory=dict)
