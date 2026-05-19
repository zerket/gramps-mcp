from pathlib import Path
from pydantic_settings import BaseSettings

ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    gramps_api_url: str = "http://localhost:5000"
    gramps_username: str = "admin"
    gramps_password: str = ""
    request_timeout: int = 30

    model_config = {
        "env_file": str(ENV_FILE) if ENV_FILE.exists() else None,
        "env_file_encoding": "utf-8",
    }


settings = Settings()
