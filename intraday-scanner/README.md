# 📊 AI Intraday Trading Scanner

**Professional-grade intraday stock scanner for NSE equities.**

Built with Python + Streamlit. Scans live market data using yfinance and identifies high-probability intraday breakout stocks using a multi-condition scoring engine.

---

## 🚀 Features

- **Live NSE Scanner** — 111 liquid stocks across 8 sectors (Banking, IT, Pharma, Auto, Finance, FMCG, Metals, Energy)
- **6-Condition Scoring** — VWAP, EMA crossover, RSI momentum, volume breakout, candle breakout, green candle
- **Real-Time Signals** — BUY (score ≥8/10), WATCH (score 6-7), AVOID (score <6)
- **Auto-Refresh** — Every 60 seconds with on/off toggle
- **Interactive Charts** — Plotly candlestick with VWAP + 5/20 EMA overlays + volume bars
- **Risk Management** — Auto-calculated target (+1.5%) and stoploss (-0.5%)
- **ML Confidence Score** — Ensemble model combining rule-based + feature-based signals
- **Anomaly Detection** — Volume & price anomaly scoring using Z-score method
- **Pattern Recognition** — Detects VWAP breakout, EMA bounce, volume climax, bullish engulfing, range breakout
- **Sentiment Analysis** — Market sentiment (Very Bullish to Very Bearish) from multi-factor model
- **Export** — CSV and Excel download
- **Dark Theme** — Bloomberg-terminal inspired professional UI

---

## 🏗 Architecture

```
                    ┌──────────────────┐
                    │   stocks_db.py   │  NSE stock universe by sector
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │    scanner.py    │  Graph-pipeline orchestrator
                    │  [FetchNode]     │  (inspired by ScrapeGraphAI)
                    │  [IndicatorNode] │
                    │  [EvalNode]      │
                    │  [ScoreNode]     │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
     ┌────────▼───┐  ┌──────▼──────┐  ┌────▼────────┐
     │indicators.py│  │   utils.py  │  │    app.py    │
     │ VWAP, EMA,  │  │ data fetch, │  │ Streamlit UI │
     │ RSI, Volume │  │ style,export│  │  Dashboard   │
     └─────────────┘  └─────────────┘  └─────────────┘
```

---

## 📁 File Structure

```
intraday-scanner/
├── app.py              # Streamlit dashboard (frontend)
├── scanner.py          # Scanning pipeline engine (backend)
├── indicators.py       # Technical indicators (VWAP, EMA, RSI)
├── ml_model.py         # ML confidence, anomaly detection, pattern recognition
├── utils.py            # Data fetching, styling, export helpers
├── stocks_db.py        # NSE stock universe by sector
├── requirements.txt    # Python dependencies
└── README.md           # This file
```

---

## ⚙️ Installation

### Local

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd intraday-scanner

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
streamlit run app.py
```

### Using virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# OR
venv\Scripts\activate     # Windows

pip install -r requirements.txt
streamlit run app.py
```

---

## ☁️ Deployment

### Streamlit Cloud (easiest)

1. Push this repo to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click "Deploy" → select repo → set main file to `app.py`
4. Done!

### HuggingFace Spaces

1. Create a new Space → SDK: **Streamlit**
2. Push this repo to the Space
3. Set `app.py` as entry point

### Render

1. Create a new Web Service
2. Build command: `pip install -r requirements.txt`
3. Start command: `streamlit run app.py --server.port $PORT`

### Railway

1. Create new project → Deploy from GitHub repo
2. Railway auto-detects Python + Streamlit
3. Start command: `streamlit run app.py`

---

## 🎯 Scoring Logic

| Condition | Criterion | Score |
|-----------|-----------|-------|
| Above VWAP | Close > VWAP | +2 |
| EMA Bullish | 5 EMA > 20 EMA | +2 |
| RSI Strong | RSI > 60 | +2 |
| Volume Breakout | Volume > 1.5× avg | +2 |
| Candle Breakout | High > Prev High | +2 |
| Green Candle | Close > Open | Prerequisite |

**Max Score: 10**

| Score | Action |
|-------|--------|
| 8-10 | 🟢 **BUY** |
| 6-7 | 🟡 **WATCH** |
| 0-5 | 🔴 **AVOID** |

## 🤖 ML/AI Features

| Feature | Method | Output |
|---------|--------|--------|
| **ML Confidence** | Ensemble: rule-based (50%) + momentum (40%) - volatility penalty (10%) | 0-100% |
| **Anomaly Detection** | Z-score on volume + price returns | 0.0 (normal) to 1.0 (anomalous) |
| **Pattern Recognition** | Candlestick + indicator analysis | VWAP breakout, EMA bounce, Volume climax, Range breakout, Bullish engulfing |
| **Sentiment** | Multi-factor: RSI, VWAP, EMA, volume, price change | Very Bullish → Very Bearish |

---

## 🛠 Configuration

### Adding stocks
Edit `stocks_db.py` and add symbols (with `.NS` suffix for NSE).

### Changing refresh interval
Edit `app.py` — change `interval=60_000` (milliseconds) in the `st_autorefresh` call.

### Adjusting scoring thresholds
Edit `indicators.py` — modify `compute_score()` and `classify_action()` functions.

### Secrets & LLM configuration (important)

This project can optionally use ScrapeGraphAI or other LLM providers for enhanced scraping and company info. Do NOT commit secrets into the repository. Recommended approaches:

- Create a local `.env` (copy `.env.example`) and add your key:

```bash
# Linux / macOS
cp .env.example .env
# edit .env and paste your key as SCRAPEGRAPHAI_CLOUD_API_KEY=

# Windows (PowerShell)
copy .env.example .env
# edit .env in Notepad and paste your key
```

- Environment variable names the code expects:
     - `SCRAPEGRAPHAI_CLOUD_API_KEY` — ScrapeGraphAI cloud key (format: `sgai-...`) (preferred)
     - `SCRAPE_LLM_API_KEY` — alternative place for an `sgai-...` key
     - `SCRAPE_LLM_PROVIDER` — `openai`, `ollama`, or `gemini` (default `ollama`)
     - `SCRAPE_LLM_MODEL` — model name (e.g. `gpt-4o`, `ollama/llama3`)

- On Windows you can also set the key permanently (PowerShell):

```powershell
setx SCRAPEGRAPHAI_CLOUD_API_KEY "sgai-..."
```

- For deployment (Streamlit Cloud, Render, Railway, etc.) use the platform's secret/env settings — do NOT put secrets in source.

If you share the key here, I will not commit it into the repo. Instead, follow one of the secure options above and the code will pick it up automatically from the environment or `.env` file.

---

## 📊 Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3.10+ |
| Framework | Streamlit |
| Data Source | yfinance |
| Charts | Plotly |
| Indicators | pandas/numpy (custom) |
| Export | openpyxl (Excel), CSV |

---

## ⚠️ Disclaimer

**For educational purposes only.** This tool does not provide financial advice. Trading involves risk. Always do your own research before making trading decisions.

---

## 📝 License

MIT
