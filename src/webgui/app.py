from flask import Flask, render_template
import os

# The template_folder is set to the 'templates' directory relative to this file's location.
app = Flask(__name__, template_folder='templates', static_folder='static')

@app.route('/')
def index():
    return render_template('index.html')

def run_webgui():
    # Get port from environment variable or use default 5012
    port = int(os.environ.get('FLASK_PORT', 5012))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    run_webgui()
