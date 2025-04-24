import requests
import sys
import re
import warnings
from pathlib import Path

# Suppress InsecureRequestWarning for unverified HTTPS
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

def restore_backup(username, password, address, file_path):
    print(f"Attempting to restore backup from {address}.")
    print("Authenticating...")
    
    # Create a session to maintain cookies
    session = requests.Session()
    
    # Authentication request
    login_data = {
        'action': 'login',
        'restore_action': 'environment',
        'autorefresh': '0',
        'command': 'auth',
        'uname': username,
        'pass': password
    }
    
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }
    
    # Make the login request
    login_response = session.post(
        address, 
        data=login_data, 
        headers=headers, 
        verify=False
    )
    
    # Save login response to extract session ID
    with open('login.html', 'w', encoding='utf-8') as f:
        f.write(login_response.text)
    
    # Extract session ID from HTML similar to bash script
    sid_cookie = None
    try:
        with open('login.html', 'r', encoding='utf-8') as f:
            login_html = f.read()
            
        # This mimics the bash grep | sed commands
        # Looking for something like "&amp;sid=12345" in the HTML
        match = re.search(r'&amp;(sid[^"]*)', login_html)
        if match:
            sid_cookie = match.group(1)
            print(f"Session id is {sid_cookie}")
        else:
            print("Failed to extract session ID from HTML")
            return
    except Exception as e:
        print(f"Failed to extract session ID: {e}")
        return
    
    # Prepare the restore request
    backup_data = {
        'action': 'backup',
        'command': 'restore'
    }
    
    # Open the file for the restore operation
    with open(file_path, 'rb') as f:
        files = {'restore_file': f}
        
        # Make the restore request with multipart/form-data
        print("Getting backup...")
        
        # Use the session ID as a cookie
        cookies = {}
        if '=' in sid_cookie:
            name, value = sid_cookie.split('=', 1)
            cookies[name] = value
        
        restore_response = session.post(
            address,
            data=backup_data,
            files=files,
            cookies=cookies,
            verify=False
        )
    
    if restore_response.status_code == 200:
        print("Backup complete")
        print("Firmware upgrade complete")
    else:
        print(f"Restore failed with status code: {restore_response.status_code}")
        print(f"Response: {restore_response.text[:100]}...")
    
    # Clean up temporary files
    try:
        Path('login.html').unlink(missing_ok=True)
    except Exception:
        pass
    
    session.close()

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python restore.py <username> <password> <address> <file>")
        sys.exit(1)
    
    username = sys.argv[1]
    password = sys.argv[2]
    address = sys.argv[3]
    file_path = sys.argv[4]
    
    restore_backup(username, password, address, file_path)