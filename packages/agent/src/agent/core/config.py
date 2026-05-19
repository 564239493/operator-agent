from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    project_name: str = "operator-agent"
    log_level: str = "INFO"
    mcp_server_command: str = "python -m mcp_server"
    static_dir: Path = Path(__file__).resolve().parent.parent / "static"


settings = Settings()
