from __future__ import annotations

from flask import Flask, jsonify, render_template, request

from services.market_data import MarketDataError, get_stock_snapshot
from services.qa_provider import QAProviderError, answer_company_question
from services.ticker_search import TickerSearchError, search_tickers


app = Flask(__name__, template_folder="templates", static_folder="static")


def error_response(message: str, status_code: int = 400, code: str = "bad_request"):
    return jsonify({"ok": False, "error": {"code": code, "message": message}}), status_code


@app.post("/api/prepare")
def api_prepare():
    payload = request.get_json(silent=True) or {}
    query = (payload.get("query") or "").strip()

    if not query:
        return error_response("Please provide a company name or ticker symbol.", 400, "missing_query")

    try:
        candidates = search_tickers(query)
    except TickerSearchError as exc:
        return error_response(str(exc), 502, "ticker_search_failed")

    if not candidates:
        return error_response("No ticker candidates found. Try a more specific name.", 404, "no_candidates")

    return jsonify(
        {
            "ok": True,
            "requires_confirmation": True,
            "query": query,
            "candidates": candidates,
        }
    )


@app.post("/api/confirm")
def api_confirm():
    payload = request.get_json(silent=True) or {}
    ticker = (payload.get("ticker") or "").strip().upper()

    if not ticker:
        return error_response("Please select a ticker before proceeding.", 400, "missing_ticker")

    try:
        snapshot = get_stock_snapshot(ticker)
    except MarketDataError as exc:
        return error_response(str(exc), 502, "market_data_failed")

    return jsonify({"ok": True, **snapshot})


@app.post("/api/qa")
def api_qa():
    payload = request.get_json(silent=True) or {}
    ticker = (payload.get("ticker") or "").strip().upper()
    question = (payload.get("question") or "").strip()

    if not ticker:
        return error_response("Ticker is required for Q&A.", 400, "missing_ticker")
    if not question:
        return error_response("Please ask a question.", 400, "missing_question")

    try:
        result = answer_company_question(ticker=ticker, question=question)
    except QAProviderError as exc:
        return error_response(str(exc), 502, "qa_provider_failed")

    return jsonify({"ok": True, **result})


@app.get("/")
@app.get("/<path:path>")
def spa(path: str | None = None):
    if path and path.startswith("api/"):
        return error_response("API route not found.", 404, "not_found")
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
