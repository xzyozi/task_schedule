# Setup Guide

This document outlines the steps to set up and run the application from a fresh clone of the repository.

## 1. Clone the Repository

First, clone the repository to your local machine using git.

```bash
git clone <repository_url>
cd task_schedule
```

## 2. Create and Activate a Virtual Environment

It is recommended to use a virtual environment to manage dependencies.

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows
.\venv\Scripts\activate
# On macOS/Linux
# source venv/bin/activate
```

## 3. Install Dependencies

Install the required Python packages using `pip`. The dependencies are listed in `pyproject.toml`.

```bash
pip install -e .
```
This command installs the project in editable mode and also installs all the dependencies.
To install dev dependencies run the following command.
```bash
pip install -e .[dev]
```


## 4. Run the Application

The application consists of two main components that need to be run separately: the FastAPI scheduler and the Flask-based Web GUI.

Open two separate terminals or command prompts, and activate the virtual environment in both.

### Terminal 1: Start the Web GUI

```bash
set PYTHONPATH=./src
python src/webgui/app.py
```

### Terminal 2: Start the FastAPI Scheduler

```bash
set PYTHONPATH=./src
python src/main.py
```

Alternatively, you can use the provided batch script on Windows to start both processes.

```bash
scripts\start_dev.bat
```

Once both components are running, you can access the Web GUI by navigating to `http://127.0.0.1:5000` in your web browser.
