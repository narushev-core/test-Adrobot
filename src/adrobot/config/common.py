from __future__ import annotations

from urllib.parse import quote_plus

from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["*"]


class DatabaseSettings(BaseModel):
    host: str
    port: int = 5432
    user: str
    password: SecretStr
    name: str

    @property
    def database_url(self) -> str:
        password = quote_plus(self.password.get_secret_value())
        return f"postgresql+asyncpg://{self.user}:{password}@{self.host}:{self.port}/{self.name}"


class KeitaroConfig(BaseModel):
    url: str
    api_key: SecretStr
    domain_id: int = 1
    traffic_source_id: int = 1
    timeout_seconds: float = 10.0


class KafkaConfig(BaseModel):
    bootstrap_servers: str = "redpanda:9092"
    events_topic: str = "adrobot.events"


class GroupsConfig(BaseModel):
    sync_interval_minutes: int = 30


class OutboxConfig(BaseModel):
    relay_interval_seconds: float = 1.0
    relay_batch_size: int = 100


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_nested_delimiter="_",
        env_nested_max_split=1,
        extra="ignore",
    )

    app: AppConfig = AppConfig()
    db: DatabaseSettings
    keitaro: KeitaroConfig
    kafka: KafkaConfig = KafkaConfig()
    groups: GroupsConfig = GroupsConfig()
    outbox: OutboxConfig = OutboxConfig()
    log_level: str = "INFO"


settings = Settings()  # type: ignore[call-arg]
