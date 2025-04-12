# will set configuration per device

# weos has a config restore function. Open consol on device and run restore command with config file. 

# create cloud appliance and connect to each device individually and apply config via the web interface. 

# TODO få till så att man kan koppla sig till webben på enheterna.   

# post till enheten med login
# #post med backup action (se webinterface)

from pathlib import Path

def device_iter(directory):
    dir_path = Path(directory)
    for file in dir_path.iterdir():
        if file.is_dir():
            print(file.name)


def ssh_conn():
    pass

if __name__ == '__main__':
    device_iter(r'topologies\one-lynx\Configuration Backups\6f57a661-5c96-49f7-b376-3fdcaee176e3')