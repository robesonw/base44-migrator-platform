from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "dev"
    app_name: str = "base44-migrator-platform"
    api_host: str = "0.0.0.0"
    api_port: int = 8080

    database_url: str
    redis_url: str

    github_token: str | None = None
    github_api_base: str = "https://api.github.com"

    workspaces_dir: str = "/data/workspaces"

settings = Settings()
