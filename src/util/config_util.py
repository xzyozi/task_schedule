import yaml
from pathlib import Path

# Assuming this file is in src/util, the project root is three levels up.
PROJECT_ROOT = Path(__file__).parent.parent.parent
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
        return self.get('core.database_url', 'sqlite:///jobs.sqlite')

# Create a single, importable instance for the application to use.
config = AppConfig()