from util.config_util import config

class CoreSettings:
    """Core application settings"""
    @property
    def DATABASE_URL(self) -> str:
        return config.database_url

settings = CoreSettings()