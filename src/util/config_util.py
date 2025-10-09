import yaml
from pathlib import Path
import json
import os
import re
from typing import Any
from util import logger_util

logger = logger_util.get_logger(__name__)

# Assuming this file is in src/util, the project root is three levels up.
_default_project_root = Path(__file__).parent.parent.parent
PROJECT_ROOT = Path(os.getenv("TASK_SCHEDULER_PROJECT_ROOT", str(_default_project_root)))
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

class AppConfig:
    """A singleton-like class to manage application configuration from a YAML file."""
    _instance = None
    _config = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(AppConfig, cls).__new__(cls)
        return cls._instance

    def __init__(self, config_path=CONFIG_PATH):
        if self._config is None:
            if not Path(config_path).exists():
                raise FileNotFoundError(f"Configuration file not found at: {config_path}")
            with open(config_path, 'r') as f:
                self._config = yaml.safe_load(f)
            self._config = self._replace_env_vars(self._config)

    def _replace_env_vars(self, config_item: Any) -> Any:
        """Recursively replaces ${VAR} or $VAR with environment variable values."""
        if isinstance(config_item, dict):
            return {k: self._replace_env_vars(v) for k, v in config_item.items()}
        elif isinstance(config_item, list):
            return [self._replace_env_vars(i) for i in config_item]
        elif isinstance(config_item, str):
            return re.sub(r'\$\{?([a-zA-Z_][a-zA-Z0-9_]*)\}?',
                          lambda match: os.getenv(match.group(1), ''),
                          config_item)
        else:
            return config_item

    def get(self, key, default=None):
        """Gets a configuration value using dot notation."""
        keys = key.split('.')
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    @property
    def api_scheme(self) -> str:
        return self.get('api.scheme', 'http')

    @property
    def api_host(self) -> str:
        return self.get('api.host', '127.0.0.1')

    @property
    def api_port(self) -> int:
        return int(self.get('api.port', 8000))

    @property
    def api_base_url(self) -> str:
        return f"{self.api_scheme}://{self.api_host}:{self.api_port}"

    @property
    def webgui_scheme(self) -> str:
        return self.get('webgui.scheme', 'http')

    @property
    def webgui_host(self) -> str:
        return self.get('webgui.host', '127.0.0.1')

    @property
    def webgui_port(self) -> int:
        return int(self.get('webgui.port', 5012))

    @property
    def webgui_base_url(self) -> str:
        return f"{self.webgui_scheme}://{self.webgui_host}:{self.webgui_port}"

    @property
    def database_url(self) -> str:
        db_url = self.get('core.database_url', 'sqlite:///jobs.sqlite')
        if db_url.startswith('sqlite:///'):
            db_file = db_url[len('sqlite:///'):]
            if db_file and not os.path.isabs(db_file) and db_file != ':memory:':
                abs_db_path = (PROJECT_ROOT / db_file).resolve()
                return f'sqlite:///{abs_db_path}'
        return db_url

    @property
    def scheduler_work_dir(self) -> Path:
        path_str = self.get('scheduler.work_dir', '~/.task_schedule/work_list')
        # Expand user home directory and resolve to an absolute path
        resolved_path = Path(path_str).expanduser().resolve()
        
        # Create the directory if it doesn't exist
        resolved_path.mkdir(parents=True, exist_ok=True)
        
        return resolved_path

    @property
    def delete_orphaned_jobs_on_sync(self) -> bool:
        return self.get('development.delete_orphaned_jobs_on_sync', False)

    @property
    def enable_db_sync(self) -> bool:
        return self.get('scheduler.enable_db_sync', False)

    @property
    def email_config(self) -> dict:
        email_conf = self.get('email', {})
        password = os.getenv('EMAIL_SENDER_PASSWORD')
        if not password and email_conf.get('smtp_server'):
            logger.warning("EMAIL_SENDER_PASSWORD environment variable is not set. Email sending may fail.")
        email_conf['smtp_password'] = password
        return email_conf

# Create a single, importable instance for the application to use.
config = AppConfig()

def read_jobs_yaml_content() -> str:
    """
    Reads the content of the jobs.yaml file.
    Raises FileNotFoundError if the file does not exist.
    """
    jobs_yaml_path = PROJECT_ROOT / "jobs.yaml"
    if not jobs_yaml_path.exists():
        raise FileNotFoundError(f"File not found: {jobs_yaml_path}")
    with open(jobs_yaml_path, "r", encoding="utf-8") as f:
        content = f.read()
    return content

NOTIFICATION_SETTINGS_FILE = "notification_settings.json"

def get_notification_settings() -> dict:
    """
    Reads the notification settings from a JSON file.
    Returns default settings if the file does not exist.
    Raises an exception if the file exists but cannot be read.
    """
    settings_path = PROJECT_ROOT / NOTIFICATION_SETTINGS_FILE
    if not settings_path.exists():
        return {"email_recipients": "", "webhook_url": ""}
    try:
        with open(settings_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
        return settings
    except Exception as e:
        # Re-raise as a more generic exception or handle as appropriate
        raise IOError(f"Failed to read notification settings from {settings_path}: {e}")

def update_notification_settings(settings: dict) -> None:
    """
    Updates the notification settings in the JSON file.
    Raises an exception if the file cannot be written.
    """
    settings_path = PROJECT_ROOT / NOTIFICATION_SETTINGS_FILE
    try:
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
        logger.info(f"Notification settings successfully updated in {settings_path}")
    except IOError as e:
        logger.error(f"Failed to write notification settings to {settings_path}: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred while writing notification settings to {settings_path}: {e}", exc_info=True)
        raise
