"""
Vercel Serverless Entrypoint for Search Autocomplete & Spell Correction Engine.
Optimized for zero-failure serverless execution with resilient path resolution and routing.
"""

from __future__ import annotations
import os
from pathlib import Path
import sys
import time
from flask import Flask, jsonify, render_template_string, request, Response

# Resolve directories
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

# Ensure both api/ and project root are in sys.path
for p in (str(BASE_DIR), str(PROJECT_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

# Import engine
try:
    from src.engine import AutocompleteEngine
except ImportError:
    from api.src.engine import AutocompleteEngine

app = Flask(__name__)

# Search for words.txt across possible serverless bundle locations
CANDIDATE_DATASET_PATHS = [
    BASE_DIR / "words.txt",
    BASE_DIR / "data" / "words.txt",
    PROJECT_ROOT / "data" / "words.txt",
    Path("data/words.txt"),
    Path("/var/task/data/words.txt"),
    Path("/var/task/api/words.txt"),
]

dataset_path = None
for cp in CANDIDATE_DATASET_PATHS:
    if cp.exists():
        dataset_path = cp
        break

# Initialize engine
engine = AutocompleteEngine()
if dataset_path is not None:
    try:
        engine.load(dataset_path, max_words=105_000)
    except Exception as e:
        print(f"Warning: Failed loading dataset from {dataset_path}: {e}", file=sys.stderr)
else:
    print("Warning: No words.txt dataset found in bundle; initializing emergency vocabulary.", file=sys.stderr)
    emergency_words = [
        ("data structures", 850_000), ("data science", 750_000), ("algorithm", 920_000),
        ("database", 810_000), ("machine learning", 890_000), ("data", 1_500_000),
        ("binary search", 420_000), ("dynamic programming", 380_000), ("hash table", 450_000),
        ("trie", 310_000), ("heap", 290_000), ("python", 880_000), ("programming", 720_000),
        ("apple", 650_000), ("application", 590_000), ("kitten", 120_000), ("sitting", 180_000),
    ]
    for w, f in emergency_words:
        engine.add(w, freq=f)

# Locate index.html
CANDIDATE_TEMPLATE_PATHS = [
    BASE_DIR / "templates" / "index.html",
    PROJECT_ROOT / "demo" / "templates" / "index.html",
    Path("demo/templates/index.html"),
    Path("/var/task/api/templates/index.html"),
]

html_template_content = ""
for tp in CANDIDATE_TEMPLATE_PATHS:
    if tp.exists():
        html_template_content = tp.read_text(encoding="utf-8")
        break


@app.route("/", methods=["GET", "POST"])
@app.route("/api", methods=["GET", "POST"])
@app.route("/api/index", methods=["GET", "POST"])
@app.route("/api/index/", methods=["GET", "POST"])
def index():
    """Render the single-page search interface or dispatch based on query parameters."""
    # If this is a POST request, dispatch to select
    if request.method == "POST":
        return select_endpoint()
    
    # If query parameter 'q' is present, dispatch to suggest
    if "q" in request.args:
        return suggest_endpoint()
        
    if html_template_content:
        return render_template_string(html_template_content, vocab_size=len(engine))
    return "<h1>Search Autocomplete Engine</h1><p>Ready. Use /suggest?q=...</p>"


@app.route("/suggest", methods=["GET"])
@app.route("/api/suggest", methods=["GET"])
@app.route("/api/index/suggest", methods=["GET"])
def suggest_endpoint():
    """Autocomplete endpoint called on each keystroke."""
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
@app.route("/api/select", methods=["POST"])
@app.route("/api/index/select", methods=["POST"])
def select_endpoint():
    """User selection endpoint to dynamically increment frequency."""
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
@app.route("/health", methods=["GET"])
@app.route("/api/stats", methods=["GET"])
@app.route("/api/health", methods=["GET"])
def health_endpoint():
    """System health check and diagnostic metadata."""
    return jsonify({
        "status": "healthy",
        "vocabulary_size": len(engine),
        "dataset_path": str(dataset_path) if dataset_path else None,
        "template_found": bool(html_template_content),
        "runtime": "Vercel Serverless Python",
    })


@app.errorhandler(404)
def fallback_router(e):
    """
    Catch-all router to handle Vercel proxy rewrite variations seamlessly.
    Ensures that any rewritten URL returns the appropriate endpoint.
    """
    if "q" in request.args:
        return suggest_endpoint()
    if request.method == "POST":
        return select_endpoint()
    raw_path = request.path.lower()
    if "health" in raw_path or "stats" in raw_path:
        return health_endpoint()
    if request.method == "GET":
        return index()
    return jsonify({"error": "Not found", "path": request.path}), 404


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
