from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):

    model_config = SettingsConfigDict(

    env_file=".env",

    env_file_encoding="utf-8",

    )

    APP_NAME: str = "Pay-Up"

    ENV: str = "development"

    DATABASE_URL: str

    JWT_SECRET: str

    JWT_ALGORITHM: str = "HS256"

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

settings = Settings()
