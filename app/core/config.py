from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_TITLE: str = "DMS Backend"
    API_V1_STR: str = "/api/v1"
    API_V2_STR: str = "/api/v2"
    API_KEY_NAME: str = "API-Key"
    VECTOR_STORES_PATH: str = "./vector_stores"
    MONGO_URL: str
    DB_NAME: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_DAYS: int

    model_config = SettingsConfigDict(env_file="./.env", extra="ignore")


settings = Settings()
