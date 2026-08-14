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

    # Deribit Options (phase 3)
    deribit_client_id: str = ""
    deribit_client_secret: str = ""
    deribit_base_url: str = "https://www.deribit.com/api/v2"
    deribit_currency: str = "BTC"

    options_min_size: float = 1.0
    options_top_legs: int = 30

    macro_symbols: dict[str, str] = {
        "spx": "^GSPC",
        "ndx": "^IXIC",
        "dxy": "DX-Y.NYB",
    }

    liquidation_bin_pct: float = 0.5
    backtest_optimize_hour: int = 3

    coinex_api_base: str = "https://api.coinex.com/v2"
    coinex_web_base: str = "https://www.coinex.com"
    coinex_market: str = "BTCUSDT"
    coinex_ai_asset: str = "btc"
    coinex_ai_lang: str = "en_US"
    coinex_enabled: bool = True
    coinex_ai_enabled: bool = True

    advisor_enabled: bool = True
    advisor_api_key: str = ""
    advisor_api_base: str = "https://api.openai.com/v1"
    advisor_model: str = "gpt-4o-mini"
    advisor_cache_minutes: int = 15

    @property
    def deribit_configured(self) -> bool:
        return bool(self.deribit_client_id and self.deribit_client_secret)

    @property
    def data_dir(self) -> Path:
        return BASE_DIR / "data"


settings = Settings()
