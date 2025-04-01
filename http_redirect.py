from flask import Flask, redirect

app = Flask(__name__)

@app.route('/generate_204')
@app.route('/gen_204')
@app.route('/hotspot-detect.html')
@app.route('/ncsi.txt')
@app.route('/connecttest.txt')
@app.route('/library/test/success.html')
@app.route('/success.txt')
@app.route('/fwlink')
@app.route('/captive.apple.com')
@app.route('/connectivitycheck.gstatic.com')
@app.route('/msftconnecttest.com')
@app.route('/')
def index():
    return redirect("https://10.0.0.1", code=302)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
