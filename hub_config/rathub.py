from flask import Flask, jsonify, render_template_string, request
import json
import logging
import requests
import paramiko
import subprocess
import threading
from datetime import datetime
import re

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Global dictionary to store the latest GPS data and status for each node
node_locations = {}
# Global variable to store the current manufacturer keyword
current_keyword = "DJI"
# Global variable to track if capture is active
capture_active = False

def get_vpn_ip():
    try:
        result = subprocess.run(['ip', 'a', 'show', 'wg0'], capture_output=True, text=True)
        output = result.stdout
        ip_match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', output)
        if ip_match:
            return ip_match.group(1)
        else:
            logging.error("Failed to find VPN IP address")
            return None
    except Exception as e:
        logging.error(f"Failed to get VPN IP: {str(e)}")
        return None

vpn_ip = get_vpn_ip()

def update_node_location(data):
    ip = data.get('ip')
    latitude = data.get('latitude')
    longitude = data.get('longitude')
    if ip and latitude and longitude:
        if ip not in node_locations:
            node_locations[ip] = {'lat': float(latitude), 'lon': float(longitude), 'status': 'normal'}
        else:
            node_locations[ip].update({'lat': float(latitude), 'lon': float(longitude)})
        logging.info(f"Updated location for {ip}: {latitude}, {longitude}")
    logging.info(f"Current node_locations: {node_locations}")

@app.route('/report', methods=['POST'])
def report():
    data = request.get_json()
    
    if not data:
        return jsonify({"status": "error", "message": "No data received"}), 400
    
    # Get the IP address from the request
    ip = request.remote_addr
    
    # Add the IP to the data dictionary
    data['ip'] = ip
    
    update_node_location(data)
    return jsonify({"status": "success"}), 200

@app.route('/node-locations')
def node_locations_endpoint():
    logging.info(f"Returning node_locations: {node_locations}")
    return jsonify(node_locations)

def get_devices_with_keyword(keyword):
    try:
        # First, get all datasources
        datasources_response = requests.get(f'http://kali:kali@{vpn_ip}:2501/datasource/all_sources.json')
        datasources_response.raise_for_status()
        datasources = datasources_response.json()

        # Create a mapping of UUID to datasource name
        uuid_to_name = {ds['kismet.datasource.uuid']: ds['kismet.datasource.name'] for ds in datasources}

        # Now get all devices
        response = requests.get(f'http://kali:kali@{vpn_ip}:2501/devices/views/all/devices.json')
        response.raise_for_status()
        devices = response.json()
        
        results = []
        for device in devices:
            manufacturer = device.get('kismet.device.base.manuf', '').lower()
            if keyword.lower() in manufacturer:
                mac = device.get('kismet.device.base.macaddr', 'Unknown MAC')
                seenby_uuids = device.get('kismet.device.base.seenby', [])
                last_seen = device.get('kismet.device.base.last_time', 0)
                last_seen_time = datetime.fromtimestamp(last_seen).strftime('%Y-%m-%d %H:%M:%S')
                node_names = []
                for seenby in seenby_uuids:
                    uuid = seenby.get('kismet.common.seenby.uuid')
                    if uuid:
                        node_name = uuid_to_name.get(uuid, f"Node {uuid}")
                        node_names.append(node_name)
                        # Update node status to 'alert'
                        for ip, data in node_locations.items():
                            if data.get('label') == node_name:
                                node_locations[ip]['status'] = 'alert'
                lat = data['lat']
                lon = data['lon']
                node_info = f"{node_name} ({lat:.6f}, {lon:.6f})"
                results.append(f"{node_info}\n{manufacturer}\n{mac}\nLast seen: {last_seen_time}")
        
        if not results:
            results.append(f"No devices found with manufacturer: {keyword}")
        
        return results
    except requests.RequestException as e:
        return [f"Error fetching devices: {str(e)}"]
    except json.JSONDecodeError as e:
        return [f"Error parsing JSON response: {str(e)}"]
    except Exception as e:
        return [f"Unexpected error: {str(e)}"]

@app.route('/')
def index():
    map_html = render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>RadiantRat</title>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.7.1/dist/leaflet.css"/>
            <script src="https://unpkg.com/leaflet@1.7.1/dist/leaflet.js"></script>
            <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 0;
                    padding: 0;
                    background-color: #f0f0f0;
                }
                #map-container {
                    position: relative;
                    height: 100vh;
                    width: 100%;
                }
                #map {
                    height: 100%;
                    width: 100%;
                }
                #ip-list, #device-alerts {
                    position: absolute;
                    top: 10px;
                    width: 300px;
                    background-color: white;
                    padding: 20px;
                    border-radius: 10px;
                    box-shadow: 0 0 10px rgba(0,0,0,0.1);
                    max-height: calc(50% - 40px);
                    overflow-y: auto;
                    z-index: 1000;
                }
                #ip-list {
                    right: 10px;
                }
                #device-alerts {
                    left: 10px;
                    display: none;
                }
                h2 {
                    color: #444;
                    border-bottom: 2px solid #444;
                    padding-bottom: 10px;
                    margin-top: 0;
                }
                ul {
                    list-style-type: none;
                    padding: 0;
                    margin: 0;
                }
                li {
                    margin-bottom: 10px;
                    padding: 10px;
                    background-color: #f9f9f9;
                    border-radius: 5px;
                }
                .node-marker {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    width: 30px;
                    height: 30px;
                    border-radius: 50%;
                    background-color: white;
                    border: 2px solid black;
                    font-weight: bold;
                    font-size: 14px;
                }
                .node-marker.active {
                    background-color: #4CAF50;
                    color: white;
                }
                .node-marker.alert {
                    background-color: #f44336;
                    color: white;
                }
                #capture-button, #keyword-input, #keyword-button {
                    position: absolute;
                    left: 50%;
                    transform: translateX(-50%);
                    padding: 10px 20px;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    cursor: pointer;
                    font-size: 16px;
                    z-index: 1001;
                }
                #capture-button {
                    bottom: 20px;
                }
                #keyword-input {
                    bottom: 70px;
                    width: 200px;
                    color: black;
                }
                #keyword-button {
                    bottom: 120px;
                    background-color: #2196F3;
                }
                #capture-button.start {
                    background-color: #4CAF50;
                }
                #capture-button.stop {
                    background-color: #f44336;
                }
                #capture-button:hover, #keyword-button:hover {
                    opacity: 0.9;
                }
            </style>
        </head>
        <body>
            <div id="map-container">
                <div id="map"></div>
                <div id="ip-list">
                    <h2>Available Nodes:</h2>
                    <ul id="ip-list-content"></ul>
                </div>
                <div id="device-alerts">
                    <h2>Alerts:</h2>
                    <ul id="device-alerts-content"></ul>
                </div>
                <input type="text" id="keyword-input" placeholder="Enter manufacturer keyword">
                <button id="keyword-button">Set Manufacturer Keyword</button>
                <button id="capture-button" class="start">Start Remote Capture</button>
            </div>
            <script>
                var map = L.map('map').setView([0, 0], 2);
                L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                }).addTo(map);
                
                var markers = {};
                var captureActive = false;

                function updateMap() {
                    $.getJSON('/node-locations', function(locations) {
                        $('#ip-list-content').empty();
                        
                        var nodes = [];
                        
                        var i = 1;
                        for (var ip in locations) {
                            var data = locations[ip];
                            var node = {
                                label: 'Node ' + i,
                                lat: data.lat,
                                lon: data.lon,
                                status: data.status
                            };
                            nodes.push(node);
                            
                            var icon = L.divIcon({
                                className: 'node-marker ' + node.status,
                                html: i
                            });
                            
                            if (markers[ip]) {
                                markers[ip].setLatLng([data.lat, data.lon]);
                                markers[ip].setIcon(icon);
                            } else {
                                markers[ip] = L.marker([data.lat, data.lon], {icon: icon}).addTo(map)
                                    .bindPopup(node.label);
                            }
                            
                            $('#ip-list-content').append('<li>Node ' + i + ': ' + ip + '<br>(' + data.lat + ', ' + data.lon + ')</li>');
                            i++;
                        }
                        
                        if (nodes.length > 0) {
                            map.fitBounds(nodes.map(node => [node.lat, node.lon]));
                        }
                    });
                }

                function updateAlerts() {
                    if (captureActive) {
                        $.getJSON('/device-alerts', function(alerts) {
                            $('#device-alerts-content').empty();
                            alerts.forEach(function(alert) {
                                $('#device-alerts-content').append('<li>' + alert + '</li>');
                            });
                        });
                        $('#device-alerts').show();
                    } else {
                        $('#device-alerts').hide();
                    }
                }

                // Update map and alerts every 10 seconds
                setInterval(function() {
                    updateMap();
                    updateAlerts();
                }, 10000);

                // Initial update
                updateMap();
                updateAlerts();

                $('#capture-button').click(function() {
                    var button = $(this);
                    if (button.hasClass('start')) {
                        $.post('/start-capture', function(response) {
                            alert(response.message);
                            button.removeClass('start').addClass('stop');
                            button.text('Stop Remote Capture');
                            captureActive = true;
                            updateAlerts();
                        });
                    } else {
                        $.post('/stop-capture', function(response) {
                            alert(response.message);
                            button.removeClass('stop').addClass('start');
                            button.text('Start Remote Capture');
                            captureActive = false;
                            updateAlerts();
                        });
                    }
                });

                $('#keyword-button').click(function() {
                    var keyword = $('#keyword-input').val();
                    $.post('/set-keyword', {keyword: keyword}, function(response) {
                        alert(response.message);
                        updateAlerts();
                    });
                });
            </script>
        </body>
        </html>
    ''')
    
    return map_html

@app.route('/device-alerts')
def device_alerts():
    global current_keyword
    alerts = get_devices_with_keyword(current_keyword)
    return jsonify(alerts)

@app.route('/set-keyword', methods=['POST'])
def set_keyword():
    global current_keyword
    new_keyword = request.form.get('keyword')
    if new_keyword:
        current_keyword = new_keyword
        return jsonify({"message": f"Keyword set to: {current_keyword}"})
    else:
        return jsonify({"message": "Invalid keyword"}), 400

def start_kismet_server():
    try:
        subprocess.Popen(["kismet", "-c", "wlan0"])
        logging.info("Kismet server started successfully")
    except Exception as e:
        logging.error(f"Failed to start Kismet server: {str(e)}")

@app.route('/start-capture', methods=['POST'])
def start_capture():
    global capture_active
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    success_count = 0
    error_messages = []

    # Start Kismet server in a separate thread
    threading.Thread(target=start_kismet_server).start()

    for i, (ip, data) in enumerate(node_locations.items(), 1):
        try:
            ssh.connect(ip, username='kali', password='kali')  # Replace with actual credentials
            command = f"kismet_cap_linux_wifi --connect {vpn_ip}:2501 --user kali --password kali --source wlan1:name=Node{i},metagps=Node{i}"
            stdin, stdout, stderr = ssh.exec_command(command)
            success_count += 1
            node_locations[ip]['status'] = 'active'
        except Exception as e:
            error_messages.append(f"Error on Node {i} ({ip}): {str(e)}")
        finally:
            ssh.close()

    capture_active = True

    if success_count == len(node_locations):
        return jsonify({"message": "Remote capture and Kismet server started successfully on all nodes."})
    elif success_count > 0:
        return jsonify({"message": f"Remote capture and Kismet server started on {success_count} out of {len(node_locations)} nodes. Errors: {'; '.join(error_messages)}"})
    else:
        return jsonify({"message": f"Failed to start remote capture on any nodes. Kismet server started locally. Errors: {'; '.join(error_messages)}"}), 500

@app.route('/stop-capture', methods=['POST'])
def stop_capture():
    global capture_active
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    success_count = 0
    error_messages = []

    for i, (ip, data) in enumerate(node_locations.items(), 1):
        try:
            ssh.connect(ip, username='kali', password='kali')  # Replace with actual credentials
            command = "pkill kismet"
            stdin, stdout, stderr = ssh.exec_command(command)
            success_count += 1
            node_locations[ip]['status'] = 'normal'
        except Exception as e:
            error_messages.append(f"Error on Node {i} ({ip}): {str(e)}")
        finally:
            ssh.close()

    # Stop local Kismet server
    try:
        subprocess.run(["pkill", "kismet"], check=True)
        logging.info("Local Kismet server stopped successfully")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to stop local Kismet server: {str(e)}")

    if success_count == len(node_locations):
        return jsonify({"message": "Remote capture stopped successfully on all nodes and local Kismet server."})
    elif success_count > 0:
        return jsonify({"message": f"Remote capture stopped on {success_count} out of {len(node_locations)} nodes and local Kismet server. Errors: {'; '.join(error_messages)}"})
    else:
        return jsonify({"message": f"Failed to stop remote capture on any nodes. Local Kismet server stopped. Errors: {'; '.join(error_messages)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4000, debug=True)  # Added debug=True for more detailed logging
