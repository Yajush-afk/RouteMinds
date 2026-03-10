from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    APP_NAME: str = "RouteMinds API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Path to the trained ML model artifact (joblib/pkl)
    MODEL_PATH: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
