from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    TELEGRAM_BOT_TOKEN: str
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/expensebot.db"
    APP_ENV: str = "dev"
    DEFAULT_CURRENCY: str = "CAD"
    LOCAL_TIMEZONE: str = "America/Edmonton"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()
