from pydantic_settings import BaseSettings, SettingsConfigDict

class CoreSettings(BaseSettings):
    """Core application settings"""
    DATABASE_URL: str = "sqlite:///jobs.sqlite"

    model_config = SettingsConfigDict(env_file=".env")

settings = CoreSettings()
