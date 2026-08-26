# Setup Guide

This document outlines the steps to set up and run the application from a fresh clone of the repository.

## 1. Clone the Repository

First, clone the repository to your local machine using git.

```bash
git clone <repository_url>
cd task_schedule
```

## 2. Create and Activate a Virtual Environment

It is recommended to use `uv` (or standard `venv`) to manage dependencies.

```bash
# Using uv (Recommended)
uv sync

# Or using standard venv
python -m venv .venv
# On Windows
.\.venv\Scripts\activate
# On macOS/Linux
# source .venv/bin/activate
```

## 3. Install Dependencies

Install the required Python packages using `pip` or `uv`. The dependencies are listed in `pyproject.toml`.

```bash
pip install -e .[dev]
```
Or with `uv`:
```bash
uv sync --extra dev
```

## 4. Run the Application

The scheduler backend and Web GUI are integrated into a single FastAPI application.

```bash
set PYTHONPATH=./src
python src/main.py
```
Or with `uv`:
```bash
uv run python src/main.py
```

Alternatively, you can use the provided batch script on Windows:

```bash
scripts\start_dev.bat
```

Once running, access the Web GUI by navigating to `http://127.0.0.1:8000` in your web browser.
