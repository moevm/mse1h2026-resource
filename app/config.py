from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "changeme"

    app_title: str = "Resource Graph Service"
    app_version: str = "0.1.0"
    debug: bool = False

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    raw_data_ttl_hours: int = 24

    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    seed_demo_on_startup: bool = True
    seed_demo_base_url: str = "http://localhost:8000"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
