# BTC Analyzer v2

ربات تحلیل جامع بیت‌کوین با جمع‌آوری داده، تحلیل چندتایم‌فریمی، داشبورد وب و اعلان تلگرام.

## قابلیت‌ها

### جمع‌آوری داده
- **OHLCV** — کندل 4h، روزانه، هفتگی
- **قیمت لحظه‌ای** — ticker 24 ساعته
- **Funding Rate** — نرخ فاندینگ فیوچرز
- **Open Interest** — حجم پوزیشن‌های باز
- **Long/Short Ratio** — نسبت لانگ به شورت
- **Taker Buy/Sell Volume** — حجم خرید/فروش
- **Fear & Greed Index** — شاخص ترس و طمع

### تحلیل
- امتیازدهی چندلایه (روند، مومنتوم، حجم، نوسان، ساختار)
- **Bollinger Bands** + **Stochastic**
- **حمایت/مقاومت** + **فیبوناچی retracement**
- تحلیل در سه تایم‌فریم: **4h / 1d / 1w**
- تشخیص رژیم بازار (Trending / Ranging / Volatile)
- فیلتر MTF Confluence
- **آنچین:** MVRV + آدرس‌های فعال (CoinMetrics)
- **ماکرو:** SPX, Nasdaq, DXY (Yahoo Finance — خودکار)
- **آپشن Deribit:** اسکرینر + Greeks — **کاملاً خودکار**
- **بک‌تست walk-forward** با Win Rate و Profit Factor

### خروجی
- **داشبورد وب** — نمودار + کارت‌های MTF
- **داشبورد آپشن** — اسکرینر Deribit + نمودار Greeks/PnL
- **تلگرام** — `/status`, `/4h`, `/1d`, `/1w` + اعلان خودکار

## نصب روی Ubuntu 24

```bash
# پیش‌نیازها
sudo apt update
sudo apt install -y python3.12-venv python3-pip git

# کلون پروژه
git clone <repo-url> btc-analyzer-v2
cd btc-analyzer-v2

# محیط مجازی
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# تنظیمات
cp .env.example .env
# ویرایش .env — توکن تلگرام و Chat ID

# راه‌اندازی دیتابیس و جمع‌آوری اولیه
PYTHONPATH=. python -m src.main init-db
PYTHONPATH=. python -m src.main collect
PYTHONPATH=. python -m src.main analyze
```

## دستورات

| دستور | توضیح |
|--------|--------|
| `python -m src.main collect` | جمع‌آوری همه داده‌ها |
| `python -m src.main analyze` | اجرای تحلیل |
| `python -m src.main backtest` | بک‌تست walk-forward |
| `python -m src.main serve` | داشبورد + API روی پورت 8000 |
| `python -m src.main telegram` | ربات تلگرام |
| `python -m src.main run` | scheduler خودکار (جمع‌آوری + تحلیل) |

## Docker

```bash
cp .env.example .env
docker compose up -d btc-analyzer    # scheduler
docker compose --profile dashboard up -d   # داشبورد روی :8080
docker compose --profile telegram up -d  # ربات تلگرام
```

## تلگرام

1. از [@BotFather](https://t.me/BotFather) ربات بسازید
2. `TELEGRAM_BOT_TOKEN` را در `.env` بگذارید
3. به ربات پیام بدهید و Chat ID را از `getUpdates` بگیرید
4. `TELEGRAM_CHAT_ID` را تنظیم کنید

## صرافی

به‌صورت پیش‌فرض `EXCHANGE_PROVIDER=auto`:
- ابتدا Binance را امتحان می‌کند
- اگر در دسترس نبود، OKX استفاده می‌شود

## API

```
GET /api/health
GET /api/v1/overview
GET /api/v1/timeframe/{4h|1d|1w}
GET /api/v1/chart/{4h|1d|1w}
GET /api/v1/signals
GET /api/v1/backtest
```

## داشبورد آپشن (Deribit)

آدرس: `http://YOUR_SERVER:8000/options.html`

در `.env`:
```env
DERIBIT_CLIENT_ID=your_id
DERIBIT_CLIENT_SECRET=your_secret
```

| حالت | توضیح |
|------|--------|
| Public | معاملات بزرگ آپشن + نمودار ریسک |
| Private | پوزیشن‌های واقعی حساب Deribit |
| Selected | کلیک روی ردیف‌های جدول |

```
GET /api/v1/options/screener?timeframe=1d&min_size=0.5
GET /api/v1/options/risk-profile?mode=auto
GET /api/v1/options/status
```

## systemd (اختیاری)

```ini
[Unit]
Description=BTC Analyzer
After=network.target

[Service]
Type=simple
User=btc
WorkingDirectory=/opt/btc-analyzer-v2
Environment=PYTHONPATH=/opt/btc-analyzer-v2
ExecStart=/opt/btc-analyzer-v2/.venv/bin/python -m src.main run
Restart=always

[Install]
WantedBy=multi-user.target
```

## ساختار پروژه

```
src/
├── collector/     # جمع‌آوری داده (Binance/OKX + Fear&Greed + On-chain)
├── analyzer/      # تحلیل تکنیکال + بک‌تست
│   ├── indicators.py
│   └── backtest.py
├── notifier/      # تلگرام
├── options/       # Deribit screener + Greeks risk profile
├── api/           # FastAPI + داشبورد
├── db/            # مدل‌های SQLite
└── main.py        # CLI
frontend/          # داشبورد وب
```

## ⚠️ هشدار

این ابزار صرفاً برای تحلیل تکنیکال است و توصیه سرمایه‌گذاری نیست.
