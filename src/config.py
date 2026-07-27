"""Application configuration — secrets via environment only (Ch.3 §3.18)."""

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
    coinex_base_url: str = "https://www.coinex.com"
    coinex_analysis_path: str = "/res/market/analysis/btc.json"

    # Binance futures reference
    binance_futures_enabled: bool = True
    binance_symbol: str = "BTCUSDT"
    binance_api_key: str = ""
    binance_api_secret: str = ""

    # Deribit options
    deribit_enabled: bool = True
    deribit_currency: str = "BTC"
    deribit_client_id: str = ""
    deribit_client_secret: str = ""
    deribit_base_url: str = "https://www.deribit.com/api/v2"

    # Bitunix execution validation
    bitunix_enabled: bool = False
    bitunix_api_key: str = ""
    bitunix_api_secret: str = ""
    bitunix_base_url: str = "https://fapi.bitunix.com"

    # Persistence
    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'btc_analyzer.db'}"

    # Scheduler (Ch.3 §3.14)
    daily_outlook_hour_utc: int = 3
    daily_outlook_minute_utc: int = 30
    # Legacy alias — minute cycle is now 1 minute per Ch.3
    collection_interval_minutes: int = 1

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
