from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gramps_api_url: str = "http://localhost:5000"
    gramps_username: str = "admin"
    gramps_password: str = ""
    request_timeout: int = 30

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
