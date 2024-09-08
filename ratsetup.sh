#!/bin/bash

if [ $EUID -ne 0 ]; then
    echo "Try again with root..."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

cat ./ratbanner.txt


read -p "Configuring node or hub? (n/h): " node_or_hub


if [[ "$node_or_hub" == "n" ]]; then
    read -p "Connect to HamVPN? (y/n): " vpnconf
    if [[ "$vpnconf" == "y" ]]; then
         cd $SCRIPT_DIR/vpn_config
         bash ./vpnsetup.sh
    fi
    cd $SCRIPT_DIR/node_config
    apt install -y gpsd-clients
    apt install -y jq
    cp ./ratnode.sh /usr/local/bin/
    cp ./ratnode.service /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable ratnode.service
    systemctl start ratnode.service
    echo ""
    echo "Node configured."
    
elif [[ "$node_or_hub" == "h" ]]; then
    read -p "Connect to HamVPN? (y/n): " vpnconf
    if [[ "$vpnconf" == "y" ]]; then 
         cd $SCRIPT_DIR/vpn_config
         bash ./vpnsetup.sh
    fi
    cd $SCRIPT_DIR/hub_config
    pip install -r ./requirements.txt
    echo ""
    echo "Dependencies installed."
    
else
    echo "Invalid input. Please enter 'n' for node or 'h' for hub."
fi
