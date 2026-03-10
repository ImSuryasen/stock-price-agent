# Project: Python-first AI Agent Stock App (Web UI + Agent)

## Goals
Build a modern single-page web app where:
1) UI is HTML/CSS/JS only for structure and rendering
2) ALL logic runs in Python (ticker resolution, stock fetch, growth metrics, QA orchestration)
3) No database or file-based storage. Everything is online and stateless.
4) The app asks for confirmation ("Proceed?") before fetching stock details.
5) Shows live/current price, previous month growth %, previous year growth %, and charts.
6) Answers user questions about the selected company using web sources (pluggable provider).
7) Modern design using Microsoft logo accent colors:
   - Orange/Red: #F25022
   - Green: #7FBA00
   - Blue: #00A4EF
   - Yellow: #FFB900
   - Gray: #737373

## Stack & Constraints
- Backend: Python 3.11+, Flask
- Data: yfinance as default provider (no DB). Provide alternative provider stub (AlphaVantage) behind env key.
- Charts: Chart.js via CDN (JS only renders chart; data comes from Python JSON endpoints)
- Frontend: Vanilla HTML/CSS/JS, minimal JS
- NO user data storage, NO caching to disk, NO analytics.

## Architecture
- Flask serves SPA static files + JSON API endpoints.
- Endpoints:
  - GET / -> SPA
  - POST /api/prepare { query } -> returns best ticker candidates and requires_confirmation=true
  - POST /api/confirm { ticker } -> returns current price + series + growth stats + company meta
  - POST /api/qa { ticker, question } -> returns grounded answer using web provider
- Separate services:
  - services/market_data.py
  - services/ticker_search.py
  - services/qa_provider.py

## Guardrails
- Never store secrets in code. Read from environment variables only.
- If web-search provider not configured, fall back to Wikipedia summary endpoint (no storage).
- Return structured errors with user-friendly messages.

## Output Requirements
- Provide a complete runnable project with:
  - requirements.txt
  - app.py
  - templates/index.html (or static/app/index.html if SPA)
  - static/styles.css
  - static/app.js
  - services/*.py
  - README.md with setup/run instructions

## Definition of Done
- `python -m venv .venv && pip install -r requirements.txt` works.
- `python app.py` runs locally and loads UI.
- Enter company name -> see ticker suggestion -> click Proceed -> see data + chart.
- Ask questions -> answer returned (web provider pluggable).