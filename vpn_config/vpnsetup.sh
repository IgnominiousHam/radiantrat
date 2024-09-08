vpnsetup(){
echo ""
echo "Checking wireguard installation..."
check_wire() {
    if command -v wg >/dev/null 2>&1; then
        echo "Wireguard already installed."
        echo ""
        return 0
    else
        echo "Installing wireguard..."
        echo ""
        return 1
    fi

}

install_wire(){
    sudo apt update
    sudo apt install wireguard
}


if ! check_wire; then
    install_wire
else
    wg-quick down wg0 > /dev/null 2>&1
fi

#read -p "Continue with new VPN setup? (y/n): " vpnconf
vpnconf="y"
if [ $vpnconf = y ] ; then
clear
echo "Generating keys..."
wg genkey | tee privatekey | wg pubkey > publickey
private=$(<privatekey)
public=$(<publickey)
#read -p "Enter VPN IP (For HamVPN use 45.79.73.38): " vpnip
#read -p "Enter VPN user (probably 'root' if using Linode): " user
user="root"
vpnip="45.79.73.38"
echo "Contacting server..."
ssh $user@$vpnip 'wg show wg0 allowed-ips | grep -v -E "10.0.0.1/32|0.0.0.0/0" | awk -F" " "{print \$2}" | awk -F"/" "{print \$1}" | sort ; wg | grep "public key" | awk -F " " "{print \$NF}"' > $radiantdir/tmpvpn.txt
awk 'NR > 1 { print previous_line } { previous_line = $0 } END { }' $radiantdir/tmpvpn.txt

server_public=$(tail -n 1 $radiantdir/tmpvpn.txt)

read -p "These IPs are already allocated. Choose something different (10.0.0.# for hubs, 10.0.1.# for remote): " newip

cat << end > /etc/wireguard/wg0.conf
[Interface]
PrivateKey = $private
Address = $newip/32
SaveConfig = true

[Peer]
PublicKey = $server_public
AllowedIPs = 0.0.0.0/0
Endpoint = $vpnip:51820

end

elif [ $vpnconf = n ] ; then
    echo "Exiting..."
    echo ""
    return 0
else
    echo "Invalid input."
    echo ""
    return 0
fi

echo "Setting server configuration..."
ssh $user@$vpnip wg set wg0 peer $public allowed-ips $newip/32
systemctl enable wg-quick@wg0.service
systemctl start wg-quick@wg0.service
wg-quick up wg0
ping -c 1 10.0.0.1 > /dev/null 2>&1
if [ $? -eq 0 ] ; then
    echo "Good to go!"
    echo ""
    return 0
else
    echo "Failed to initialize connection, turning VPN interface off..."
    wg-quick down wg0
    echo ""
    return 0
fi
rm $radiantdir/tmpvpn.txt
}


vpnsetup
