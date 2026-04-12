#!/usr/bin/env python3
"""
Sprawdzarka Offline – interfejs webowy
Uruchom:  python app.py
Otwórz:   http://localhost:5000
"""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request, send_file, abort

from judge_core import (
    JudgeResult,
    VERDICT_COLORS,
    VERDICT_LABELS,
    judge_submission,
    load_config,
)

BASE_DIR = Path(__file__).parent
app = Flask(__name__)
app.secret_key = os.urandom(24)

config = load_config(str(BASE_DIR / "zadanie" / "config.json"))

ZADANIE_DIR = BASE_DIR / "zadanie"


# ──────────────────────────────────────────────
# Pomocnicze
# ──────────────────────────────────────────────

LANGUAGE_DISPLAY = {
    "cpp":    "C++",
    "c":      "C",
    "python": "Python 3",
    "java":   "Java",
    "pascal": "Pascal",
    "?":      "Nieznany",
}

EXTENSION_FOR_LANG = {
    "cpp":    ".cpp",
    "c":      ".c",
    "python": ".py",
    "java":   ".java",
    "pascal": ".pas",
}


def find_pdf() -> Path | None:
    """Zwraca ścieżkę do pierwszego pliku .pdf w folderze zadanie/, lub None."""
    pdfs = sorted(ZADANIE_DIR.glob("*.pdf"))
    return pdfs[0] if pdfs else None


def result_to_dict(r: JudgeResult) -> dict:
    return {
        "problem_name":       r.problem_name,
        "language":           LANGUAGE_DISPLAY.get(r.language, r.language),
        "compilation_error":  r.compilation_error,
        "total_points":       round(r.total_points, 2),
        "max_points":         round(r.max_points, 2),
        "score_pct":          r.score_pct,
        "tests": [
            {
                "name":             t.test_name,
                "verdict":          t.verdict,
                "verdict_label":    VERDICT_LABELS.get(t.verdict, t.verdict),
                "verdict_color":    VERDICT_COLORS.get(t.verdict, "secondary"),
                "time_ms":          t.time_ms,
                "points":           round(t.points, 2),
                "max_points":       round(t.max_points, 2),
                "expected_preview": t.expected_preview,
                "got_preview":      t.got_preview,
                "error_msg":        t.error_msg,
            }
            for t in r.tests
        ],
    }


# ──────────────────────────────────────────────
# Trasy
# ──────────────────────────────────────────────

@app.get("/")
def index():
    problem_name = config.get("problem_name", "Zadanie")
    time_limit   = config.get("time_limit", 2.0)

    in_dir = BASE_DIR / config["in_dir"]
    test_count = len(list(in_dir.glob("*.in")))

    pdf = find_pdf()

    return render_template(
        "index.html",
        problem_name=problem_name,
        time_limit=time_limit,
        test_count=test_count,
        has_pdf=pdf is not None,
        pdf_name=pdf.name if pdf else "",
    )


@app.get("/pdf")
def serve_pdf():
    """Serwuje plik PDF z treścią zadania."""
    pdf = find_pdf()
    if pdf is None:
        abort(404)
    return send_file(pdf, mimetype="application/pdf")


@app.post("/api/judge")
def api_judge():
    data = request.get_json(force=True)
    code     = data.get("code", "").strip()
    language = data.get("language", "cpp")
    filename = data.get("filename", "")

    if not code:
        return jsonify({"error": "Brak kodu źródłowego."}), 400

    if filename:
        ext = Path(filename).suffix.lower()
    else:
        ext = EXTENSION_FOR_LANG.get(language, ".cpp")
        filename = f"solution{ext}"

    if not filename.lower().endswith(ext):
        filename += ext

    result = judge_submission(
        source_code=code,
        filename=filename,
        config=config,
        base_dir=BASE_DIR,
    )

    return jsonify(result_to_dict(result))


@app.post("/api/upload")
def api_upload():
    """Przyjmuje plik przez multipart/form-data."""
    if "file" not in request.files:
        return jsonify({"error": "Brak pliku."}), 400

    f = request.files["file"]
    filename = f.filename or "solution.cpp"
    code = f.read().decode("utf-8", errors="replace")

    ext = Path(filename).suffix.lower()
    from judge_core import LANGUAGE_EXTENSIONS
    language = LANGUAGE_EXTENSIONS.get(ext, "cpp")

    result = judge_submission(
        source_code=code,
        filename=filename,
        config=config,
        base_dir=BASE_DIR,
    )

    return jsonify(result_to_dict(result))


if __name__ == "__main__":
    print("=" * 50)
    print("  Sprawdzarka Offline")
    print(f"  Zadanie: {config.get('problem_name', 'Zadanie')}")
    print(f"  Limit czasu: {config.get('time_limit', 2)}s")
    pdf = find_pdf()
    if pdf:
        print(f"  Treść: {pdf.name}")
    print("  Otwórz: http://localhost:5000")
    print("=" * 50)
    app.run(debug=False, host="127.0.0.1", port=5000)
