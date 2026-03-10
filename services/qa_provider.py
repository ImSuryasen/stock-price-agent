from __future__ import annotations

import os
import re
from typing import Any

import requests
import yfinance as yf


class QAProviderError(Exception):
    pass


def _resolve_company_name(ticker: str) -> str:
    try:
        info = yf.Ticker(ticker).info or {}
        return str(info.get("shortName") or info.get("longName") or ticker)
    except Exception:
        return ticker


def _safe_trim(text: str, max_chars: int = 500) -> str:
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "..."


def _company_info_from_yfinance(ticker: str) -> dict[str, str]:
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception:
        info = {}

    return {
        "company_name": str(info.get("shortName") or info.get("longName") or ticker),
        "website": str(info.get("website") or "").strip(),
        "summary": str(info.get("longBusinessSummary") or info.get("shortBusinessSummary") or "").strip(),
    }


def _is_price_question(question: str) -> bool:
    return bool(
        re.search(
            r"\b(stock\s*price|share\s*price|current\s*price|trading\s*at|quote|market\s*price)\b",
            question.lower(),
        )
    )


def _wikipedia_summary(company_name: str) -> tuple[str, str | None]:
    search_resp = requests.get(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "list": "search",
            "srsearch": company_name,
            "format": "json",
            "srlimit": 1,
        },
        timeout=15,
    )
    search_resp.raise_for_status()
    search_data = search_resp.json()
    hits = search_data.get("query", {}).get("search", [])
    if not hits:
        return "", None

    title = hits[0].get("title")
    if not title:
        return "", None

    summary_resp = requests.get(
        f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
        timeout=15,
    )
    summary_resp.raise_for_status()
    summary_data = summary_resp.json()

    extract = str(summary_data.get("extract") or "")
    page_url = f"https://en.wikipedia.org/wiki/{str(title).replace(' ', '_')}"
    return extract, page_url


def _search_duckduckgo(query: str) -> tuple[list[str], list[str]]:
    resp = requests.get(
        "https://api.duckduckgo.com/",
        params={"q": query, "format": "json", "no_redirect": 1, "no_html": 1},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    snippets: list[str] = []
    sources: list[str] = []

    abstract_text = str(data.get("AbstractText") or "").strip()
    abstract_url = str(data.get("AbstractURL") or "").strip()
    if abstract_text:
        snippets.append(abstract_text)
    if abstract_url.startswith("http://") or abstract_url.startswith("https://"):
        sources.append(abstract_url)

    for topic in data.get("RelatedTopics", [])[:5]:
        text = str(topic.get("Text") or "").strip()
        first_url = str(topic.get("FirstURL") or "").strip()
        if text:
            snippets.append(text)
        if first_url.startswith("http://") or first_url.startswith("https://"):
            sources.append(first_url)

        for nested in topic.get("Topics", [])[:3]:
            nested_text = str(nested.get("Text") or "").strip()
            nested_url = str(nested.get("FirstURL") or "").strip()
            if nested_text:
                snippets.append(nested_text)
            if nested_url.startswith("http://") or nested_url.startswith("https://"):
                sources.append(nested_url)

    return snippets, sources


def _search_serpapi(query: str) -> tuple[list[str], list[str]]:
    api_key = os.getenv("SERPAPI_API_KEY", "").strip()
    if not api_key:
        return [], []

    resp = requests.get(
        "https://serpapi.com/search.json",
        params={"q": query, "api_key": api_key, "engine": "google", "num": 5},
        timeout=20,
    )
    resp.raise_for_status()
    payload = resp.json()

    snippets: list[str] = []
    sources: list[str] = []
    for item in (payload.get("organic_results", []) or [])[:5]:
        snippet = str(item.get("snippet") or "").strip()
        link = str(item.get("link") or "").strip()
        if snippet:
            snippets.append(snippet)
        if link.startswith("http://") or link.startswith("https://"):
            sources.append(link)

    return snippets, sources


def _fetch_yahoo_quote(ticker: str) -> tuple[str, str | None]:
    try:
        resp = requests.get(
            "https://query1.finance.yahoo.com/v7/finance/quote",
            params={"symbols": ticker},
            timeout=15,
        )
        resp.raise_for_status()
        payload = resp.json()
        results = payload.get("quoteResponse", {}).get("result", []) or []
        if results:
            first = results[0]
            price = first.get("regularMarketPrice")
            currency = str(first.get("currency") or "")
            if price is not None:
                answer = f"Latest Yahoo Finance quote for {ticker}: {price} {currency}."
                return answer, f"https://finance.yahoo.com/quote/{ticker}"
    except requests.RequestException:
        pass

    # Fallback to yfinance quote metadata if direct quote endpoint is unavailable.
    try:
        yf_ticker = yf.Ticker(ticker)
        fast_info = yf_ticker.fast_info or {}
        price = fast_info.get("lastPrice")
        currency = str(fast_info.get("currency") or "")
        if price is None:
            info = yf_ticker.info or {}
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            if not currency:
                currency = str(info.get("currency") or "")
    except Exception as exc:
        raise QAProviderError("Could not find a live quote for the selected ticker.") from exc

    if price is None:
        raise QAProviderError("Live quote data is unavailable right now.")

    answer = f"Latest web quote for {ticker}: {price} {currency}."
    return answer, f"https://finance.yahoo.com/quote/{ticker}"


def _is_ai_synthesis_enabled() -> bool:
    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
    azure_key = os.getenv("AZURE_OPENAI_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    return bool((azure_endpoint and azure_key) or openai_key)


def _build_azure_chat_url(endpoint: str, deployment: str, api_version: str) -> str:
    base = endpoint.rstrip("/")

    if "/openai/deployments/" in base:
        if base.endswith("/chat/completions"):
            return f"{base}?api-version={api_version}"
        return f"{base}/chat/completions?api-version={api_version}"

    if "/openai" in base:
        return f"{base}/deployments/{deployment}/chat/completions?api-version={api_version}"

    return f"{base}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"


def _call_azure_openai(messages: list[dict[str, str]]) -> str:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
    key = os.getenv("AZURE_OPENAI_KEY", "").strip()
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini").strip()
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview").strip()
    if not endpoint or not key:
        raise QAProviderError("Azure OpenAI is not configured.")

    url = _build_azure_chat_url(endpoint=endpoint, deployment=deployment, api_version=api_version)
    resp = requests.post(
        url,
        headers={"Content-Type": "application/json", "api-key": key},
        json={"messages": messages, "temperature": 0.2, "max_tokens": 280},
        timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()
    try:
        return str(payload["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise QAProviderError("Azure OpenAI returned an unexpected response.") from exc


def _call_openai_compatible(messages: list[dict[str, str]]) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise QAProviderError("OPENAI_API_KEY is not configured.")

    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

    resp = requests.post(
        f"{base_url}/chat/completions",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        json={"model": model, "messages": messages, "temperature": 0.2, "max_tokens": 280},
        timeout=30,
    )
    resp.raise_for_status()
    payload = resp.json()
    try:
        return str(payload["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise QAProviderError("OpenAI-compatible provider returned an unexpected response.") from exc


def _synthesize_with_ai(*, ticker: str, company_name: str, question: str, snippets: list[str], sources: list[str]) -> str:
    context_snippets = "\n".join([f"- {_safe_trim(s, 380)}" for s in snippets[:6]])
    source_list = "\n".join([f"- {u}" for u in sources[:8]])

    messages = [
        {
            "role": "system",
            "content": (
                "You are a web-grounded financial research assistant. "
                "Answer only from provided snippets. If evidence is weak, explicitly say uncertainty. "
                "Keep answer concise (2-5 sentences) and practical."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Ticker: {ticker}\n"
                f"Company: {company_name}\n"
                f"Question: {question}\n\n"
                f"Web snippets:\n{context_snippets}\n\n"
                f"Source URLs:\n{source_list}\n\n"
                "Provide the best possible answer using only the snippets above."
            ),
        },
    ]

    azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
    azure_key = os.getenv("AZURE_OPENAI_KEY", "").strip()
    if azure_endpoint and azure_key:
        return _call_azure_openai(messages)
    return _call_openai_compatible(messages)


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def answer_company_question(ticker: str, question: str) -> dict[str, Any]:
    company_info = _company_info_from_yfinance(ticker)
    company_name = str(company_info.get("company_name") or _resolve_company_name(ticker))
    query = f"{company_name} ({ticker}) {question}".strip()

    wikipedia_extract = ""
    wikipedia_url: str | None = None

    try:
        wikipedia_extract, wikipedia_url = _wikipedia_summary(company_name)
    except requests.RequestException:
        wikipedia_extract, wikipedia_url = "", None

    serpapi_snippets: list[str] = []
    serpapi_sources: list[str] = []
    ddg_snippets: list[str] = []
    ddg_sources: list[str] = []

    try:
        serpapi_snippets, serpapi_sources = _search_serpapi(query)
    except requests.RequestException:
        serpapi_snippets, serpapi_sources = [], []

    try:
        ddg_snippets, ddg_sources = _search_duckduckgo(query)
    except requests.RequestException:
        ddg_snippets, ddg_sources = [], []

    sources: list[str] = []
    snippets: list[str] = []

    if wikipedia_extract:
        snippets.append(wikipedia_extract)
    snippets.extend(serpapi_snippets)
    snippets.extend(ddg_snippets)

    if wikipedia_url:
        sources.append(wikipedia_url)
    sources.extend(serpapi_sources)
    sources.extend(ddg_sources)

    website = str(company_info.get("website") or "").strip()
    if website.startswith("http://") or website.startswith("https://"):
        sources.append(website)

    summary = str(company_info.get("summary") or "").strip()
    if summary:
        snippets.append(summary)
        sources.append(f"https://finance.yahoo.com/quote/{ticker}/profile")

    if _is_price_question(question):
        try:
            quote_answer, quote_url = _fetch_yahoo_quote(ticker)
            snippets.insert(0, quote_answer)
            if quote_url:
                sources.insert(0, quote_url)
        except requests.RequestException:
            pass

    deduped_snippets = _dedupe(snippets)
    deduped_sources = _dedupe(sources)

    if not deduped_snippets:
        raise QAProviderError("Could not find enough web results for this question. Please try rephrasing it.")

    if _is_ai_synthesis_enabled():
        try:
            ai_answer = _synthesize_with_ai(
                ticker=ticker,
                company_name=company_name,
                question=question,
                snippets=deduped_snippets,
                sources=deduped_sources,
            )
            if ai_answer:
                return {
                    "provider": "websearch+ai",
                    "answer": _safe_trim(ai_answer, 900),
                    "sources": deduped_sources[:10],
                }
        except (requests.RequestException, QAProviderError):
            # Fall through to deterministic summary when AI call fails.
            pass

    return {
        "provider": "websearch",
        "answer": _safe_trim(" ".join(deduped_snippets[:3]), 900),
        "sources": deduped_sources[:10],
    }
