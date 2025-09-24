# Resilient Task Scheduler

A resilient, persistent, and manageable task scheduling service designed for production environments. This project evolves a simple task scheduler into a robust, API-driven service with a web-based management UI.

As described in the design documentation, this system is built to be a stateful, observable, and flexible scheduler, moving beyond the limitations of simple in-process schedulers.

## Features

*   **Resilient & Persistent**: Powered by `APScheduler` with a `SQLAlchemyJobStore` backend (SQLite, PostgreSQL), ensuring jobs and schedules persist across application restarts and crashes.
*   **Dynamic Configuration**: Define and manage jobs through a human-readable `jobs.yaml` file. No code changes or redeployments are needed for schedule adjustments.
*   **Hot-Reloading**: The scheduler automatically detects changes to `jobs.yaml` and applies them without requiring a service restart, enabling zero-downtime configuration updates.
*   **Web-based GUI**: A comprehensive web interface for managing and monitoring the scheduler, including:
    *   A dashboard with system status and a job timeline.
    *   A job management view to list, filter, create, pause, resume, and manually trigger jobs.
    *   Detailed job history and log views (`stdout`/`stderr`).
*   **REST API Control**: A FastAPI-based REST API provides full programmatic control over the scheduler, allowing for integration with other systems.
*   **Extensible Job Types**: Natively supports scheduling both Python functions and any external command or script (e.g., shell scripts, batch files).
*   **Advanced Scheduling**: Supports cron-based, interval-based, and date-based scheduling with fine-grained control over execution (e.g., `max_instances`, `coalesce`, `misfire_grace_time`).

## Technology Stack

*   **Backend**: Python 3.8+
*   **Scheduling**: APScheduler
*   **API**: FastAPI
*   **Web GUI**: Flask
*   **Database/ORM**: SQLAlchemy (with support for SQLite, PostgreSQL)
*   **Configuration**: PyYAML for `jobs.yaml`, Pydantic for validation
*   **File Monitoring**: Watchdog

## Getting Started

### 1. Installation

Clone the repository and install the project and its dependencies. This project uses `pyproject.toml` for packaging.

```bash
git clone <repository-url>
cd task_schedule
pip install .
```

For development, you can install the optional development dependencies:
```bash
pip install .[dev]
```

### 2. Running the Application

The application is packaged as a command-line script. Once installed, you can start the scheduler and the web API/GUI with a single command:

```bash
task-scheduler
```

By default, this will start the FastAPI server on `http://localhost:8000`. The web GUI will be accessible at a different port specified in the configuration (e.g., `http://localhost:5012`).

## Usage

### Defining Jobs in `jobs.yaml`

Jobs are defined as a list of job objects in the `jobs.yaml` file in the project root.

**Example: Python Function Job**
This job runs a Python function every 5 minutes.

```yaml
- id: 'api_health_check'
  func: 'modules.scheduler.tasks.monitoring.check_api_status'
  description: 'Checks the health of the main API endpoint every 5 minutes.'
  is_enabled: true
  trigger:
    type: 'interval'
    minutes: 5
  kwargs:
    api_endpoint: 'http://127.0.0.1:8000/'
  replace_existing: true
```

**Example: External Script Job**
This job runs a shell script on a cron schedule.

```yaml
- id: 'daily_backup'
  func: '/path/to/your/backup_script.sh'
  description: 'Runs the daily backup shell script.'
  is_enabled: true
  trigger:
    type: 'cron'
    day_of_week: 'mon-sun'
    hour: '2'
    minute: '30'
  replace_existing: true
```

### Using the Web Interface

The web interface provides a user-friendly way to interact with the scheduler. Navigate to the GUI's URL in your browser to:
- View the status of all jobs.
- Manually trigger, pause, or resume jobs.
- Create new jobs using a guided form.
- View the execution history and logs for any job.

## Project Structure

- `jobs.yaml`: The main configuration file for defining jobs.
- `pyproject.toml`: Project definition, dependencies, and packaging information.
- `src/`: Main application source code.
  - `src/core/`: Core components like database configuration and CRUD operations.
  - `src/modules/scheduler/`: The main APScheduler logic, including the job loader, router, and tasks.
  - `src/webgui/`: The Flask-based web interface.
- `doc/`: Project design and architecture documents.
- `test/`: Test files.
