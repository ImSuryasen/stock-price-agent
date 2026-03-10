---
name: stock-agent-python-webapp
description: Build a Python-first AI agent web app that fetches live stock prices, computes 1M/1Y growth, renders charts, and answers company questions via web sources with a proceed/confirm workflow. Use Flask + yfinance + Chart.js, no storage.
license: MIT
metadata:
  stack: [python, flask, html, css, js, chartjs, yfinance]
  constraints: [no_database, no_filesystem_storage, online_only, python_logic_only]
---

# Stock Agent Skill (Python-first Web App)

## When to use
Use this skill when the user wants:
- A web app with HTML/CSS/JS structure but Python-only business logic
- Live/current stock prices + historical chart
- Previous month and previous year growth metrics
- Confirmation (“Proceed?”) before fetching
- Q&A about the selected company grounded in web sources
- No data storage

## Output checklist (must satisfy)
1) Flask SPA catch-all route serving index.html
2) JSON APIs:
   - POST /api/prepare {query}
   - POST /api/confirm {ticker}
   - POST /api/qa {ticker, question}
3) services modules:
   - services/ticker_search.py
   - services/market_data.py
   - services/qa_provider.py
4) UI:
   - input for company/ticker
   - candidate selection + Proceed
   - KPI cards (current, 1M growth, 1Y growth)
   - chart (Chart.js renders, Python provides data)
   - Q&A panel
5) Microsoft color accents:
   - #F25022 #7FBA00 #00A4EF #FFB900 #737373
6) No storage: no DB, no writing to disk, no user profiles

## Implementation guidance (step-by-step)
### A) Scaffold
- Create requirements.txt with:
  flask, yfinance, pandas
- Create app.py with:
  - catch-all SPA routing
  - /api/prepare, /api/confirm, /api/qa

### B) Ticker resolution
- Accept company name OR ticker.
- Use yfinance search (if available) to find best quote.
- Return multiple candidates for confirmation.

### C) Market data + growth
- Pull 1y daily history.
- last_close = last trading day close
- month_close = close nearest to ~30 days ago (first available in last 1mo)
- year_close = close nearest to ~365 days ago (first available in last 1y)
- Compute pct growth and return.

### D) Confirmation flow
- /api/prepare returns requires_confirmation=true and candidates
- UI requires Proceed button to call /api/confirm

### E) Q&A
- Always answer in context of selected ticker/company.
- Prefer web-backed sources. If no provider configured, fallback to Wikipedia summary + yfinance metadata.
- Return: {answer, sources:[urls]}

## Edge cases
- No ticker matches -> show error and request a different query
- Market data empty -> friendly failure and suggestion
- Rate limits -> suggest switching to AlphaVantage provider via API key
- Non-US tickers -> allow suffix like .NS, .L, etc.

## Example prompts this skill should handle
- “Build the stock agent app exactly as specified”
- “Add proceed/confirm before pulling live stock”
- “Show month/year growth with charts”
- “Add Q&A with web sources, no storage”
