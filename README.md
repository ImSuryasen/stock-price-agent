# Stock Price Agent (Python-First)

Modern Flask single-page app where all business logic lives in Python: ticker search, stock snapshot retrieval, growth metrics, and grounded company Q&A.

## Features

- SPA with Flask catch-all routing
- Prepare flow with confirmation step before loading stock details
- Endpoints:
  - POST /api/prepare
  - POST /api/confirm
  - POST /api/qa
- Provider-based market data
  - Default: yfinance
  - Optional stub path: AlphaVantage using env key
- Provider-based Q&A
  - Always retrieves live web context first (Wikipedia, DuckDuckGo, optional SerpAPI)
  - Uses AI synthesis when configured (Azure OpenAI or OpenAI-compatible)
  - Falls back to deterministic web-grounded summary when no AI key is set
- Chart.js line chart and KPI cards (current price, month growth, year growth)

## Project Structure

- app.py
- requirements.txt
- services/
  - ticker_search.py
  - market_data.py
  - qa_provider.py
- templates/
  - index.html
- static/
  - styles.css
  - app.js

## Setup

1. Create and activate a virtual environment.

   Windows PowerShell:

   python -m venv .venv
   .venv\Scripts\Activate.ps1

2. Install dependencies.

   pip install -r requirements.txt

3. Optional environment variables.

   - MARKET_DATA_PROVIDER=yfinance or alphavantage
   - ALPHAVANTAGE_API_KEY=your_key_here
    - AZURE_OPENAI_ENDPOINT=https://<your-resource>.openai.azure.com
    - AZURE_OPENAI_KEY=your_key_here
    - AZURE_OPENAI_DEPLOYMENT=your_deployment_name (default: gpt-4o-mini)
    - AZURE_OPENAI_API_VERSION=2024-02-15-preview
    - OPENAI_API_KEY=your_key_here (optional OpenAI-compatible fallback)
    - OPENAI_BASE_URL=https://api.openai.com/v1 (optional override)
    - OPENAI_MODEL=gpt-4o-mini (optional)
    - SERPAPI_API_KEY=your_key_here (optional extra web search)

4. Run app.

   python app.py

5. Open browser.

   http://127.0.0.1:5000

## API Contract

POST /api/prepare

Request body:

{
  "query": "Microsoft"
}

Response body (success):

{
  "ok": true,
  "requires_confirmation": true,
  "query": "Microsoft",
  "candidates": [
    {
      "ticker": "MSFT",
      "name": "Microsoft Corporation",
      "exchange": "NMS"
    }
  ]
}

POST /api/confirm

Request body:

{
  "ticker": "MSFT"
}

Response includes:

- company metadata
- current_price
- growth.month_pct and growth.year_pct
- series array for chart rendering

POST /api/qa

Request body:

{
  "ticker": "MSFT",
  "question": "What does this company do?"
}

Response includes:

- provider
- answer
- sources

## Notes

- The app is stateless and does not store user data.
- No database, no file caching, no analytics.
- Secrets are read from environment variables only.

## Shared Agent Skill

This repo includes a shareable Agent Skill at [agent_skills/stock-agent/SKILL.md](agent_skills/stock-agent/SKILL.md).

Use this skill when asking an agent to build or extend this app pattern (Python-first logic, proceed/confirm workflow, stock metrics, chart rendering, and grounded Q&A with no storage).
