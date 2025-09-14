from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings"""
    DATABASE_URL: str = "sqlite:///jobs.sqlite"

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
