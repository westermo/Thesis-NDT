class Device:
    def __init__(self, name=None):
        self.name = name           # Str: Hostname?
        self.id = None             # Str: ID from xml?
        self.position = None       # Tuple[int, int]: (x, y)
        self.family = None         # Str: "Lynx"
        self.model = None          # Str: "L110-F2G"
        self.image = None          # Str: "WeOS-5.24"
        self.ip_address = None     # Str: "198.18.2.143"
        self.net_mask = None       # Str: "255.255.255.0"
        self.ports = {}            # Dict[str, Port]: 

class Port:
    def __init__(self, name=None):
        self.name = name           # Str: "GigabitEthernet1/0/1"
        self.id = None             # Str or Int: "Gi1/0/1" or 101
        self.mac_address = None    # Str: "00:07:7C:4D:31:C1"
        self.up = None             # Bool: True=up, False=down

# Example dictionary of devices
devices_dict = {
    "device1": {
        "name": "redfox-4d-31-c0",
        "id": "a80f1106-01c5-42ea-a254-47e9df0d05ec",
        "position": (-3.17, 8.92),
        "family": "RedFox",
        "model": "RedFox-5528-F4G-T24G-LV",
        "image": "WeOS-5.24",
        "ip_address": "198.18.2.67",
        "net_mask": "255.255.255.0",
        "ports": {
            "port1": {
                "name": "eth1",
                "id": "0",
                "mac_address": "00:07:7C:4D:31:C1",
                "up": False,
            },
            "port2": {
                "name": "eth2",
                "id": "1",
                "mac_address": "00:07:7C:4D:31:C2",
                "up": False,
            }
        }
    },
    "device2": {
        "name": "kompis",
        "id": "123ad481-2a0f-4a61-8e23-1684c36f98d7",
        "position": (-3.17, 8.92),
        "family": "Wolverine",
        "model": "DDW-142",
        "image": "WeOS-5.24",
        "ip_address": "198.18.2.201",
        "net_mask": "255.255.255.0",
        "ports": {
            "port1": {
                "name": "ETH 1",
                "id": "0",
                "mac_address": "00:07:7C:10:87:C3",
                "up": True,
            },
            "port2": {
                "name": "ETH 2",
                "id": "1",
                "mac_address": "00:07:7C:10:87:C4",
                "up": True,
            }
        }
    },
    "device3": {
        "name": "lynx-59-93-a0",
        "id": "93650786-e7c9-40e9-bf90-b82808c0c569",
        "position": (-3.17, 8.92),
        "family": "Lynx",
        "model": "Lynx-3510-E-F2G-P8G-LV",
        "image": "WeOS-5.24",
        "ip_address": "198.18.2.145",
        "net_mask": "255.255.255.0",
        "ports": {
            "port1": {
                "name": "eth1",
                "id": "0",
                "mac_address": "00:11:B4:59:93:A1",
                "up": False,
            },
            "port2": {
                "name": "eth2",
                "id": "1",
                "mac_address": "00:11:B4:59:93:A2",
                "up": False,
            },
            "port3": {
                "name": "eth3",
                "id": "2",
                "mac_address": "00:11:B4:59:93:A3",
                "up": False,
            },
            "port4": {
                "name": "eth4",
                "id": "3",
                "mac_address": "00:11:B4:59:93:A4",
                "up": False,
            }
        }
    }
}


# list to store devices
device_list = []

# Iterate through the Example dictionary and create Device objects
# see https://stackoverflow.com/questions/3294889/iterating-over-dictionaries-using-for-loops
for device_id, device_data in devices_dict.items():
    # Create a new Device object
    device = Device()
    
    # Set device attributes (excluding ports)
    for attr_name, attr_value in device_data.items():
        if attr_name != "ports":
            # setting the attributes of the object here.
            setattr(device, attr_name, attr_value)
    
    # Don't override the id with the dictionary key
    # device.id = device_id
    
    # Process ports if they exist
    if "ports" in device_data:
        for port_id, port_data in device_data["ports"].items():
            # Create a new Port object
            port = Port()
            
            # Set port attributes
            for port_attr, port_value in port_data.items():
                setattr(port, port_attr, port_value)
            
            # Add the port to the device's ports dictionary
            device.ports[port_id] = port
    
    # Add the device to our list
    device_list.append(device)

"""
for device in device_list:
    print(f"\nDevice Details for: {device.name}")
    print(f"ID: {device.id}")
    print(f"Position: {device.position}")
    print(f"Family: {device.family}")
    print(f"Model: {device.model}")
    print(f"Image: {device.image}")
    print(f"IP Address: {device.ip_address}")
    print(f"Net Mask: {device.net_mask}")
    
    print("Ports:")
    for port_id, port in device.ports.items():
        print(f"  Port: {port.name}")
        print(f"    ID: {port.id}")
        print(f"    MAC Address: {port.mac_address}")
        print(f"    Status: {'Up' if port.up else 'Down'}")
    
    print("-" * 50)  # Add a separator between devices
"""

for device in device_list:
    print(f"\nDevice Details for: {device.name}")
    for attr, value in device.__dict__.items():
        if attr != "ports":  # Handle ports separately
            print(f"{attr}: {value}")
    
    print("Ports:")
    for port_id, port in device.ports.items():
        print(f"  Port: {port.name}")
        for port_attr, port_value in port.__dict__.items():
            print(f"    {port_attr}: {port_value}")
    
    print("-" * 50)