"""
Vercel Serverless Entrypoint for Autocomplete & Spellcheck Engine.
"""

from __future__ import annotations
from pathlib import Path
import sys
import time
from flask import Flask, jsonify, render_template, request

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.engine import AutocompleteEngine

app = Flask(
    __name__,
    template_folder=str(PROJECT_ROOT / "demo" / "templates"),
    static_folder=str(PROJECT_ROOT / "demo" / "static"),
)

# Initialize engine globally
DATASET_PATH = PROJECT_ROOT / "data" / "words.txt"
engine = AutocompleteEngine(DATASET_PATH, max_words=105_000)


@app.route("/")
def index():
    """Render the single-page search interface."""
    return render_template("index.html", vocab_size=len(engine))


@app.route("/suggest", methods=["GET"])
def suggest_endpoint():
    """
    Autocomplete endpoint called on each keystroke.
    """
    query = request.args.get("q", "").strip()
    k_param = request.args.get("k", "5")
    try:
        k = max(1, min(20, int(k_param)))
    except ValueError:
        k = 5

    if not query:
        return jsonify({
            "query": "",
            "latency_us": 0.0,
            "latency_ms": 0.0,
            "suggestions": [],
            "did_you_mean": None,
            "corrections": [],
            "fell_back": False,
        })

    t0 = time.perf_counter()
    result = engine.suggest(query, k=k)
    elapsed_us = (time.perf_counter() - t0) * 1_000_000.0

    payload = result.to_dict()
    payload["latency_us"] = round(elapsed_us, 2)
    payload["latency_ms"] = round(elapsed_us / 1000.0, 4)
    return jsonify(payload)


@app.route("/select", methods=["POST"])
def select_endpoint():
    """
    User selection endpoint to dynamically increment frequency.
    """
    data = request.get_json(silent=True) or {}
    word = data.get("word") or request.form.get("word") or request.args.get("word")
    if not word:
        return jsonify({"success": False, "error": "Missing 'word' parameter"}), 400

    delta = 500
    new_freq = engine.select(word, delta=delta)
    return jsonify({
        "success": True,
        "word": word,
        "new_freq": new_freq,
        "boost": delta,
    })


@app.route("/stats", methods=["GET"])
def stats_endpoint():
    """System and vocabulary status."""
    return jsonify({
        "vocabulary_size": len(engine),
        "status": "ready",
        "runtime": "Vercel Serverless Python",
    })


# For local testing
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
