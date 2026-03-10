from __future__ import annotations

import os
from typing import Any

import requests
import yfinance as yf


class MarketDataError(Exception):
    pass


def _pct_growth(previous: float | None, current: float | None) -> float | None:
    if previous is None or current is None or previous == 0:
        return None
    return round(((current - previous) / previous) * 100.0, 2)


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_series(history_df) -> list[dict[str, float | str]]:
    if history_df is None or history_df.empty:
        raise MarketDataError("No market history available for this ticker.")

    series = []
    for idx, row in history_df.iterrows():
        close_price = _to_float(row.get("Close"))
        if close_price is None:
            continue
        series.append(
            {
                "date": idx.strftime("%Y-%m-%d"),
                "close": round(close_price, 4),
            }
        )

    if not series:
        raise MarketDataError("No usable close-price data found for this ticker.")

    return series


def _approx_close(series: list[dict[str, float | str]], trading_days_ago: int) -> float | None:
    if not series:
        return None
    idx = max(0, len(series) - 1 - trading_days_ago)
    return _to_float(series[idx].get("close"))


def _get_snapshot_from_yfinance(ticker: str) -> dict[str, Any]:
    stock = yf.Ticker(ticker)
    history = stock.history(period="1y", interval="1d", auto_adjust=False)
    series = _build_series(history)

    if len(series) < 2:
        raise MarketDataError("Not enough daily close data to compute growth metrics.")

    last_close = _to_float(series[-1]["close"])
    if last_close is None:
        raise MarketDataError("Latest close price is missing for this ticker.")

    current_price = None
    try:
        fast_info = stock.fast_info or {}
        current_price = _to_float(fast_info.get("lastPrice"))
    except Exception:
        current_price = None

    if current_price is None:
        try:
            info = stock.info or {}
            current_price = _to_float(info.get("currentPrice") or info.get("regularMarketPrice"))
        except Exception:
            current_price = None

    if current_price is None:
        current_price = last_close

    close_approx_1mo_ago = _approx_close(series, trading_days_ago=22)
    close_approx_1y_ago = _approx_close(series, trading_days_ago=252)

    info = {}
    try:
        info = stock.info or {}
    except Exception:
        info = {}

    company_name = str(info.get("shortName") or info.get("longName") or ticker)
    currency = str(info.get("currency") or "N/A")
    exchange = str(info.get("exchange") or info.get("fullExchangeName") or "N/A")

    return {
        "ticker": ticker,
        "company_name": company_name,
        "currency": currency,
        "exchange": exchange,
        "current_price": current_price,
        "last_close": last_close,
        "month_growth_pct": _pct_growth(close_approx_1mo_ago, last_close),
        "year_growth_pct": _pct_growth(close_approx_1y_ago, last_close),
        "series": series,
    }


def _get_snapshot_from_alphavantage(ticker: str) -> dict[str, Any]:
    api_key = os.getenv("ALPHAVANTAGE_API_KEY", "").strip()
    if not api_key:
        raise MarketDataError("AlphaVantage is selected but ALPHAVANTAGE_API_KEY is missing.")

    quote_resp = requests.get(
        "https://www.alphavantage.co/query",
        params={"function": "GLOBAL_QUOTE", "symbol": ticker, "apikey": api_key},
        timeout=15,
    )
    quote_resp.raise_for_status()
    quote_data = quote_resp.json().get("Global Quote", {})

    daily_resp = requests.get(
        "https://www.alphavantage.co/query",
        params={"function": "TIME_SERIES_DAILY_ADJUSTED", "symbol": ticker, "outputsize": "compact", "apikey": api_key},
        timeout=20,
    )
    daily_resp.raise_for_status()
    series_map = daily_resp.json().get("Time Series (Daily)", {})
    if not series_map:
        raise MarketDataError("AlphaVantage did not return historical data for this ticker.")

    points = []
    for day, vals in sorted(series_map.items()):
        close = _to_float(vals.get("4. close"))
        if close is None:
            continue
        points.append({"date": day, "close": round(close, 4)})

    if len(points) < 2:
        raise MarketDataError("Not enough AlphaVantage history to compute growth metrics.")

    current_price = _to_float(points[-1]["close"])
    month_ago_price = _to_float(points[-22]["close"]) if len(points) > 22 else _to_float(points[0]["close"])
    year_ago_price = _to_float(points[0]["close"])

    if current_price is None:
        raise MarketDataError("AlphaVantage did not return a valid current price.")

    last_close = _to_float(points[-1]["close"])
    if last_close is None:
        raise MarketDataError("AlphaVantage did not return a valid latest close.")

    return {
        "ticker": ticker,
        "company_name": ticker,
        "currency": "N/A",
        "exchange": "N/A",
        "current_price": current_price,
        "last_close": last_close,
        "month_growth_pct": _pct_growth(month_ago_price, last_close),
        "year_growth_pct": _pct_growth(year_ago_price, last_close),
        "series": points,
    }


def get_stock_snapshot(ticker: str) -> dict[str, Any]:
    provider = os.getenv("MARKET_DATA_PROVIDER", "yfinance").strip().lower()

    try:
        if provider == "alphavantage":
            return _get_snapshot_from_alphavantage(ticker)
        return _get_snapshot_from_yfinance(ticker)
    except requests.RequestException as exc:
        raise MarketDataError("Market data provider is temporarily unavailable.") from exc
    except MarketDataError:
        raise
    except Exception as exc:
        raise MarketDataError("Unable to fetch stock details right now. Please try again.") from exc
