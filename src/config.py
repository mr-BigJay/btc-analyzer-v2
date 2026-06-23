from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    symbol: str = "BTCUSDT"
    futures_symbol: str = "BTCUSDT"
    okx_inst_id: str = "BTC-USDT"
    okx_swap_id: str = "BTC-USDT-SWAP"
    exchange_provider: str = "auto"  # auto | binance | okx

    database_url: str = f"sqlite:///{BASE_DIR / 'data' / 'btc_analyzer.db'}"

    klines_limit: int = 500
    collection_interval_minutes: int = 15

    binance_spot_base: str = "https://api.binance.com"
    binance_futures_base: str = "https://fapi.binance.com"

    timeframes: list[str] = ["4h", "1d", "1w"]

    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    alert_threshold: int = 70
    daily_report_hour: int = 8

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    @property
    def data_dir(self) -> Path:
        return BASE_DIR / "data"


settings = Settings()
