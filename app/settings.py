from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    OPENROUTER_API_KEY: str
    OPENROUTER_MODEL: str = "openai/gpt-4o-mini"
    OPENROUTER_SITE_URL: str | None = None  # для заголовка HTTP-Referer
    OPENROUTER_APP_NAME: str | None = None  # для X-Title

    TELEGRAM_BOT_TOKEN: str

    PUBLIC_BASE_URL: str | None = None  # для вебхука
    USE_WEBHOOK: bool = False

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

settings = Settings()