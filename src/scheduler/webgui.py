from flask import Flask, render_template_string
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Task Scheduler WebGUI</title>
        <style>
            body { font-family: sans-serif; margin: 20px; background-color: #f4f4f4; color: #333; }
            h1 { color: #0056b3; }
            .container { background-color: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .info { background-color: #e9ecef; padding: 15px; border-radius: 5px; margin-top: 20px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Task Scheduler WebGUI</h1>
            <p>This is a placeholder for the Task Scheduler's Web-based Graphical User Interface.</p>
            <div class="info">
                <p><strong>Status:</strong> Running</p>
                <p><strong>Port:</strong> 5000 (default Flask port)</p>
                <p>Further development will integrate job management and monitoring features here.</p>
            </div>
        </div>
    </body>
    </html>
    """)

def run_webgui():
    # Get port from environment variable or use default 5000
    port = int(os.environ.get('FLASK_PORT', 5000))
    app.run(host='0.0.0.0', port=port)

if __name__ == '__main__':
    run_webgui()
