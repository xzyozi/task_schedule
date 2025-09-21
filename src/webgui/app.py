from flask import Flask, render_template
import os
import requests

# The template_folder is set to the 'templates' directory relative to this file's location.
app = Flask(__name__, template_folder='templates', static_folder='static')

# Configuration
API_BASE_URL = "http://localhost:8000"

@app.route('/')
def index():
    summary_data = {
        "total_jobs": 0,
        "running_jobs": 0,
        "successful_runs": 0,
        "failed_runs": 0
    }
    timeline_data = []
    try:
        summary_response = requests.get(f"{API_BASE_URL}/api/dashboard/summary")
        summary_response.raise_for_status()
        summary_data = summary_response.json()

        timeline_response = requests.get(f"{API_BASE_URL}/api/dashboard/timeline")
        timeline_response.raise_for_status()
        timeline_data = timeline_response.json()

    except requests.exceptions.RequestException as e:
        print(f"Could not connect to API: {e}")
        pass

    return render_template('index.html', summary=summary_data, timeline=timeline_data)

@app.route('/logs')
def logs():
    return render_template('logs.html')

@app.route('/jobs')
def jobs():
    return render_template('jobs.html')

def run_webgui():
    # Get port from environment variable or use default 5012
    port = int(os.environ.get('FLASK_PORT', 5012))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    run_webgui()
