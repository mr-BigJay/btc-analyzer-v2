"""BTC Analyzer v3 — configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # CoinEx narrative
    coinex_enabled: bool = True

    # Binance futures reference
    binance_futures_enabled: bool = True
    binance_symbol: str = "BTCUSDT"

    # Deribit options
    deribit_enabled: bool = True
    deribit_currency: str = "BTC"
    deribit_client_id: str = ""
    deribit_client_secret: str = ""
    deribit_base_url: str = "https://www.deribit.com/api/v2"

    # Bitunix execution
    bitunix_enabled: bool = False
    bitunix_api_key: str = ""
    bitunix_api_secret: str = ""

    # Persistence
    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'btc_analyzer.db'}"

    # Scheduler
    daily_outlook_hour_utc: int = 3
    daily_outlook_minute_utc: int = 30
    collection_interval_minutes: int = 15

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    @property
    def data_dir(self) -> Path:
        return BASE_DIR / "data"

    @property
    def deribit_configured(self) -> bool:
        return bool(self.deribit_client_id and self.deribit_client_secret)


settings = Settings()
