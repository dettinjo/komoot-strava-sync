from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str = "redis://redis:6379"
    SECRET_KEY: str
    KOMOOT_ENCRYPTION_KEY: str
    STRAVA_CLIENT_ID: str
    STRAVA_CLIENT_SECRET: str
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    LICENSE_SERVER_URL: str = ""
    ENVIRONMENT: str = "production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    STRAVA_REDIRECT_URI: str = "http://localhost:8000/auth/strava/callback"
    STRAVA_WEBHOOK_VERIFY_TOKEN: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
