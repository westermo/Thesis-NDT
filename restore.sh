# Example usage: ./backup.sh admin admin https://1.2.3.4 mybackup.formatType
username=$1 #The username to user for authentication (admin)
password=$2 #The password to use for authentication (admin)
address=$3 #The network location of the target, i.e https://1.2.3.4
file=$4 #path to file to restore (.json)
echo "Attempting to get backup from $address."
echo "Authenticating..."
curl -X POST $address -k -b cookies -c cookies -H "Content-Type: application/x-www-form-urlencoded" -d "action=login&restore_action=environment&autorefresh=0&command=auth&uname=$username&pass=$password" > login.html
sidCookie=$(grep sid login.html -m 1 | sed "s/.*&amp;sid/sid/g" | sed 's/".*//g')
echo "Session id is $sidCookie"
echo "Getting backup.."
curl -X POST $address -k -b $sidCookie -c cookies -H "Content-Type: multipart/form-data" -F 'action=backup' -F 'command=restore' -F "restore_file=@$file"
echo "Backup complete"
echo "Firmware upgrade complete"

rm cookies
rm login.html