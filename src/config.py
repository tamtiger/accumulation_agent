from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Infrastructure configs
    db_url: str = Field("postgresql://postgres:postgrespassword@localhost:5432/abas_db", validation_alias="DB_URL")
    redis_url: str = Field("redis://localhost:6379/0", validation_alias="REDIS_URL")
    telegram_bot_token: str = Field("", validation_alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field("", validation_alias="TELEGRAM_CHAT_ID")
    binance_api_key: str = Field("", validation_alias="BINANCE_API_KEY")
    binance_secret: str = Field("", validation_alias="BINANCE_SECRET")
    binance_enable_rate_limit: bool = Field(True, validation_alias="BINANCE_ENABLE_RATE_LIMIT")

    # Strategy configurations
    reserve_floor: float = Field(0.15, validation_alias="RESERVE_FLOOR")
    daily_deployment_cap: float = Field(0.05, validation_alias="DAILY_DEPLOYMENT_CAP")
    hot_exchange_cap: float = Field(0.25, validation_alias="HOT_EXCHANGE_CAP")
    min_profit_threshold: float = Field(0.00375, validation_alias="MIN_PROFIT_THRESHOLD")
    core_btc_target: float = Field(0.70, validation_alias="CORE_BTC_TARGET")
    trading_target: float = Field(0.15, validation_alias="TRADING_TARGET")
    trading_floor: float = Field(0.05, validation_alias="TRADING_FLOOR")
    promotion_threshold: float = Field(1.3, validation_alias="PROMOTION_THRESHOLD")
    inv3_epsilon: float = Field(1e-8, validation_alias="INV3_EPSILON")
    delta_neutral_enabled: bool = Field(False, validation_alias="DELTA_NEUTRAL_ENABLED")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

def load_settings() -> Settings:
    """
    Loads settings from environment variables and the .env file.
    """
    return Settings()

# Global settings instance
settings = load_settings()
