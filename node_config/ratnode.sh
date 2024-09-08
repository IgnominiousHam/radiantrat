#!/bin/bash
GPSD_SERVER="localhost"
GPSD_PORT="2947"
# Change to hub IP
SERVER_URL="http://10.0.0.5:4000/report"
INTERVAL=1

report_location(){
gps_data=$(gpspipe -w -n 5 | grep -m 1 TPV | jq -r '.lat, .lon')
echo $gps_data
    if [ -n "$gps_data" ]; then
        lat=$(echo $gps_data | awk -F' ' '{ print $1 }')
        lon=$(echo $gps_data | awk -F' ' '{ print $2 }')
        # Send data to server
        curl -X POST "$SERVER_URL" \
             -H "Content-Type: application/json" \
             -d "{\"latitude\": \"$lat\", \"longitude\": \"$lon\"}"
    fi
}

while true; do
report_location
sleep $INTERVAL
done
