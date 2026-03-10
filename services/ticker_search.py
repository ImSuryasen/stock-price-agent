from __future__ import annotations

from typing import Any

import yfinance as yf


class TickerSearchError(Exception):
    pass


def _extract_score_hint(quote: dict[str, Any]) -> str:
    score = quote.get("score")
    if score is not None:
        try:
            return f"search-score:{float(score):.3f}"
        except (TypeError, ValueError):
            pass

    if quote.get("isYahooFinance"):
        return "high-confidence"

    quote_type = str(quote.get("quoteType") or "").upper()
    if quote_type:
        return f"type:{quote_type.lower()}"

    return "candidate"


def _candidate_from_quote(quote: dict[str, Any]) -> dict[str, str]:
    return {
        "ticker": str(quote.get("symbol", "")).upper(),
        "name": str(quote.get("shortname") or quote.get("longname") or "Unknown Company"),
        "exchange": str(quote.get("exchange") or "N/A"),
        "score_hint": _extract_score_hint(quote),
    }


def search_tickers(query: str, limit: int = 5) -> list[dict[str, str]]:
    try:
        search = yf.Search(query=query, max_results=limit, news_count=0)
        quotes = search.quotes or []
    except Exception as exc:
        raise TickerSearchError("Could not search tickers at the moment. Please try again.") from exc

    candidates: list[dict[str, str]] = []
    seen = set()
    for quote in quotes:
        symbol = str(quote.get("symbol", "")).upper()
        if not symbol or symbol in seen:
            continue
        seen.add(symbol)
        candidates.append(_candidate_from_quote(quote))
        if len(candidates) >= limit:
            break

    if not candidates:
        fallback = query.strip().upper().replace(" ", "")
        if fallback:
            candidates.append(
                {
                    "ticker": fallback,
                    "name": query.title(),
                    "exchange": "N/A",
                    "score_hint": "fallback-from-query",
                }
            )

    return candidates
