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
- **لیکوئیدیشن:** نقشه از OKX (خودکار)
- **SMC:** FVG, BOS/CHoCH, Order Block (از کندل‌ها)
- **بک‌تست:** walk-forward + بهینه‌سازی خودکار پارامترها
- **آپشن Deribit:** اسکرینر + Greeks — **کاملاً خودکار**

### خروجی
- **داشبورد وب** — نمودار + کارت‌های MTF + ماکرو
- **داشبورد آپشن** — اسکرینر Deribit + نمودار Greeks (خودکار)
- **تلگرام** — `/status`, `/4h`, `/1d`, `/1w` + اعلان خودکار

> **اصل طراحی:** هیچ ورودی دستی لازم نیست — scheduler همه داده‌ها را جمع و تحلیل می‌کند.

## نصب روی Ubuntu 24 (یک دستور)

### نصب با یک خط (پیشنهادی — root یا کاربر عادی)

```bash
bash -c 'set -euo pipefail; D="${BTC_ANALYZER_DIR:-$HOME/btc-analyzer-v2}"; R="https://github.com/mr-BigJay/btc-analyzer-v2.git"; B="${BTC_ANALYZER_BRANCH:-main}"; if ! command -v git >/dev/null 2>&1; then export DEBIAN_FRONTEND=noninteractive; apt-get update -qq; apt-get install -y git; fi; if [[ -d "$D/.git" ]]; then git -C "$D" fetch origin "$B"; git -C "$D" checkout "$B"; git -C "$D" reset --hard "origin/$B"; else git clone --branch "$B" "$R" "$D"; fi; chmod +x "$D/install.sh"; exec "$D/install.sh" "$@"' sh
```

اگر پوشه از قبل وجود دارد، خودکار آپدیت و نصب می‌کند. با `root` هم کار می‌کند.

### نصب دستی (۴ خط)

```bash
git clone https://github.com/mr-BigJay/btc-analyzer-v2.git
cd btc-analyzer-v2
chmod +x install.sh
./install.sh
```

اسکریپت `install.sh` **همه‌چیز را خودکار** انجام می‌دهد:
- نصب پیش‌نیازهای سیستم (`python3-venv`, `git`, ...)
- `git pull` از شاخه `main`
- ساخت/آپدیت venv و پکیج‌های Python
- `init-db` → `collect` → `analyze` → `optimize`
- نصب و ری‌استارت سرویس **systemd** (پیش‌فرض روی Linux)
- توقف پروسه/سرویس قدیمی
- تأیید نسخه داشبورد (`Dashboard v2` در هدر)

### آپدیت بعدی

```bash
cd btc-analyzer-v2
./install.sh
```

همین — نیازی به `git pull`، `systemctl restart` یا کار دستی دیگر نیست.

### گزینه‌های اختیاری

| دستور | توضیح |
|--------|--------|
| `./install.sh` | نصب یا آپدیت کامل (پیش‌فرض) |
| `./install.sh --no-optimize` | بدون بهینه‌سازی بک‌تست |
| `./install.sh --docker` | اجرا با Docker به‌جای systemd |
| `./install.sh --no-systemd` | فقط برای محیط توسعه |
| `./install.sh status` | وضعیت سرویس و API |

### نصب دستی (اختیاری)

```bash
sudo apt update && sudo apt install -y python3.12-venv python3-pip git
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
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
| `python -m src.main optimize` | بهینه‌سازی پارامترها (خودکار روزانه) |
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
GET /api/v1/liquidations
GET /api/v1/optimized-params
```

## داشبورد آپشن (Deribit)

آدرس: `http://YOUR_SERVER:8000/options.html`

**کاملاً خودکار** — هر ۱۵ دقیقه با scheduler جمع‌آوری می‌شود. نیازی به Fetch یا کلیک نیست.

برای پوزیشن‌های شخصی (اختیاری، یک‌بار در `.env`):
```env
DERIBIT_CLIENT_ID=your_id
DERIBIT_CLIENT_SECRET=your_secret
```

```
GET /api/v1/options/latest      # screener + risk profile
GET /api/v1/options/screener
GET /api/v1/options/risk-profile
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
