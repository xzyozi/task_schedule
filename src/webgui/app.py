from flask import Flask, Response, jsonify, render_template, request
import requests

# The template_folder is set to the 'templates' directory relative to this file's location.
app = Flask(__name__, template_folder="templates", static_folder="static")

from util.config_util import config

# Configuration
API_BASE_URL = config.api_base_url
API_BACKEND_URL = config.api_base_url


def _backend_headers() -> dict:
    """バックエンドAPI呼び出し用の共通ヘッダー(認証キーを含む)を返す。"""
    if config.internal_api_key:
        return {"X-API-Key": config.internal_api_key}
    return {}


@app.route("/webgui-config")
def webgui_config():
    return jsonify({"API_BASE_URL": API_BASE_URL})


@app.route("/")
def index():
    summary_data = {"total_jobs": 0, "running_jobs": 0, "successful_runs": 0, "failed_runs": 0}
    try:
        response = requests.get(f"{API_BASE_URL}/api/dashboard/summary", headers=_backend_headers())
        response.raise_for_status()  # Raise an exception for bad status codes
        summary_data = response.json()
    except requests.exceptions.RequestException as e:
        # Log the error or handle it as needed
        print(f"Could not connect to API: {e}")
        # The view will render with default zero values
        pass

    return render_template("index.html", summary=summary_data)


@app.route("/logs")
def logs():
    return render_template("logs.html")


@app.route("/jobs")
def jobs():
    return render_template("jobs.html")


@app.route("/workflows")
def workflows():
    return render_template("workflows.html")


@app.route("/workflows/<int:workflow_id>")
def workflow_detail(workflow_id):
    return render_template("workflow_detail.html", workflow_id=workflow_id)


@app.route("/jobs/<job_id>")
def job_detail(job_id):
    return render_template("job_detail.html", job_id=job_id)


@app.route("/api/timeline-data")
def timeline_data():
    try:
        response = requests.get(f"{API_BASE_URL}/api/timeline/data", headers=_backend_headers())
        response.raise_for_status()
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        print(f"Error fetching timeline data from backend API: {e}")
        return jsonify({"error": "Could not fetch timeline data"}), 500


@app.route("/api/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
def api_proxy(path):
    """A generic proxy for all /api/ requests."""
    try:
        # Construct the full API URL
        url = f"{API_BACKEND_URL}/api/{path}"

        # Forward the request, injecting the internal API key so the
        # backend's authentication (core.auth.verify_api_key) succeeds
        # even when the browser client doesn't know the key itself.
        proxied_headers = {key: value for (key, value) in request.headers if key != "Host"}
        proxied_headers.update(_backend_headers())

        # Forward the request
        resp = requests.request(
            method=request.method,
            url=url,
            headers=proxied_headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            params=request.args,
        )

        # Exclude certain headers from being forwarded
        excluded_headers = ["content-encoding", "content-length", "transfer-encoding", "connection"]
        headers = [(name, value) for (name, value) in resp.raw.headers.items() if name.lower() not in excluded_headers]

        # Create a response to send back to the client
        response = Response(resp.content, resp.status_code, headers)
        return response

    except requests.exceptions.RequestException as e:
        print(f"Error proxying request to API: {e}")
        return jsonify({"error": "API proxy error"}), 502


@app.route("/settings")
def settings():
    return render_template("settings.html")


def run_webgui():
    # The extra_files parameter makes the dev server watch config.yaml for changes.
    app.run(
        host=config.webgui_host,
        port=config.webgui_port,
        debug=True,  # debug=True enables the reloader
        extra_files=["config.yaml"],
    )


if __name__ == "__main__":
    run_webgui()
