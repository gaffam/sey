from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    API_KEY: str | None = None
    DATABASE_URL: str = (
        "postgresql+asyncpg://postgres:postgres@localhost/gambusia?connect_timeout=5"
    )
    TWILIO_SID: str | None = None
    TWILIO_TOKEN: str | None = None
    TWILIO_NUMBER: str | None = None
    ALERT_PHONE: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

def get_settings() -> Settings:
    return Settings()

settings = get_settings()

if not settings.API_KEY:
    print("Warning: API_KEY not set")
