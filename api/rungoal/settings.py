from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(frozen=True, env_file="../.env", extra="ignore")

    # Required
    JWT_ACCESS_TOKEN_KEY: str
    JWT_REFRESH_TOKEN_KEY: str
    GOOGLE_REFRESH_TOKEN_KEY: str

    RUNTRACKER_DB: str

    # Optional
    DEV: bool = False
    DEBUG_SQL: bool = False


settings = Settings.model_validate({})
