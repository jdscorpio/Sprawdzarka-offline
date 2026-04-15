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
    LANGUAGE_EXTENSIONS,
    judge_submission,
    load_config,
)

BASE_DIR = Path(__file__).parent
app = Flask(__name__)
app.secret_key = os.urandom(24)


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


def discover_tasks() -> dict[str, dict]:
    """
    Przeszukuje główny katalog projektu w poszukiwaniu folderów zadań.
    Folder jest traktowany jako zadanie, jeśli zawiera plik config.json.
    """
    tasks: dict[str, dict] = {}
    for d in sorted(BASE_DIR.iterdir()):
        if not d.is_dir():
            continue
        cfg_path = d / "config.json"
        if not cfg_path.exists():
            continue
        task_id = d.name
        cfg = load_config(str(cfg_path))
        in_path = BASE_DIR / cfg.get("in_dir", f"{task_id}/in")
        test_count = len(list(in_path.glob("*.in"))) if in_path.exists() else 0
        pdfs = sorted(d.glob("*.pdf"))
        tasks[task_id] = {
            "id":           task_id,
            "dir":          d,
            "config":       cfg,
            "problem_name": cfg.get("problem_name", task_id),
            "time_limit":   float(cfg.get("time_limit", 2.0)),
            "test_count":   test_count,
            "pdf":          pdfs[0] if pdfs else None,
        }
    return tasks


TASKS = discover_tasks()
DEFAULT_TASK_ID = next(iter(TASKS)) if TASKS else None


def get_task(task_id: str | None) -> dict | None:
    if task_id and task_id in TASKS:
        return TASKS[task_id]
    return TASKS.get(DEFAULT_TASK_ID) if DEFAULT_TASK_ID else None


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


def tasks_for_template() -> list[dict]:
    """Zwraca metadane zadań do użycia w szablonach (bez ścieżek wewnętrznych)."""
    return [
        {
            "id":           t["id"],
            "problem_name": t["problem_name"],
            "time_limit":   t["time_limit"],
            "test_count":   t["test_count"],
            "has_pdf":      t["pdf"] is not None,
            "pdf_name":     t["pdf"].name if t["pdf"] else "",
        }
        for t in TASKS.values()
    ]


# ──────────────────────────────────────────────
# Trasy
# ──────────────────────────────────────────────

@app.get("/")
def index():
    if not TASKS:
        return "Brak zadań. Utwórz folder z plikiem config.json.", 404

    return render_template(
        "index.html",
        tasks=tasks_for_template(),
        default_task_id=DEFAULT_TASK_ID,
    )


@app.get("/pdf")
def serve_pdf():
    """Serwuje plik PDF dla zadania wskazanego parametrem ?task=<id>."""
    task_id = request.args.get("task", DEFAULT_TASK_ID)
    task = get_task(task_id)
    if task is None or task["pdf"] is None:
        abort(404)
    return send_file(task["pdf"], mimetype="application/pdf")


@app.get("/api/tasks")
def api_tasks():
    """Zwraca listę wszystkich dostępnych zadań."""
    return jsonify(tasks_for_template())


@app.post("/api/judge")
def api_judge():
    data = request.get_json(force=True)
    code     = data.get("code", "").strip()
    language = data.get("language", "cpp")
    filename = data.get("filename", "")
    task_id  = data.get("task_id", DEFAULT_TASK_ID)

    if not code:
        return jsonify({"error": "Brak kodu źródłowego."}), 400

    task = get_task(task_id)
    if task is None:
        return jsonify({"error": "Nieznane zadanie."}), 400

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
        config=task["config"],
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
    task_id = request.form.get("task_id", DEFAULT_TASK_ID)

    ext = Path(filename).suffix.lower()
    language = LANGUAGE_EXTENSIONS.get(ext, "cpp")

    task = get_task(task_id)
    if task is None:
        return jsonify({"error": "Nieznane zadanie."}), 400

    result = judge_submission(
        source_code=code,
        filename=filename,
        config=task["config"],
        base_dir=BASE_DIR,
    )

    return jsonify(result_to_dict(result))


if __name__ == "__main__":
    print("=" * 50)
    print("  Sprawdzarka Offline")
    print(f"  Znaleziono zadań: {len(TASKS)}")
    for t in TASKS.values():
        pdf_info = f" [PDF: {t['pdf'].name}]" if t["pdf"] else ""
        print(f"    - {t['id']}: {t['problem_name']} ({t['test_count']} testów){pdf_info}")
    print("  Otwórz: http://localhost:5000")
    print("=" * 50)
    app.run(debug=False, host="127.0.0.1", port=5000)
