import requests
import sys
from requests.auth import HTTPBasicAuth

def backup(username, password, host, file):
    print(f"Attempting to restore backup from {host}.")
    print("Authenticating...")

    login_data = {
        'action': 'login',
        'restore_action': 'environment',
        'autorefresh': '0',
        'command': 'auth',
        'uname': username,
        'pass': password
    }

    session = requests.Session()
    response = session.post(host, data=login_data, verify=False)
    
    if response.status_code == 200:
        sid_cookie = response.cookies.get('sid')
        print(f"Session id is {sid_cookie}")
        
        print("Getting backup...")
        backup_data = {
            'action': 'backup',
            'command': 'restore'
        }
        files = {'restore_file': open(file, 'rb')}
        response = session.post(host, data=backup_data, files=files, verify=False)
        
        if response.status_code == 200:
            print("Backup complete")
            print("Firmware upgrade complete")
        else:
            print("Failed to get backup")
    else:
        print("Authentication failed")

    session.close()

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python backup.py <username> <password> <address> <file>")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    host = sys.argv[3]
    file = sys.argv[4]

    backup(username, password, host, file)

#run by "python3 \win_restore.py username password host file"