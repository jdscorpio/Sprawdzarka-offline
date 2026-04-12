"""
Sprawdzarka Offline – silnik oceniania
"""

from __future__ import annotations

import json
import platform
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

IS_WINDOWS = platform.system() == "Windows"
EXE_SUFFIX = ".exe" if IS_WINDOWS else ""

# ──────────────────────────────────────────────
# Konfiguracja
# ──────────────────────────────────────────────

DEFAULT_CONFIG: dict = {
    "time_limit": 2.0,
    "memory_limit": 256,
    "in_dir": "in",
    "out_dir": "out",
    "problem_name": "Zadanie",
    "test_groups": None,
}

LANGUAGE_EXTENSIONS: dict[str, str] = {
    ".cpp": "cpp",
    ".cc":  "cpp",
    ".cxx": "cpp",
    ".c":   "c",
    ".py":  "python",
    ".java": "java",
    ".pas": "pascal",
}


def load_config(config_path: str = "config.json") -> dict:
    cfg = DEFAULT_CONFIG.copy()
    p = Path(config_path)
    if p.exists():
        with open(p, encoding="utf-8") as f:
            cfg.update(json.load(f))
    return cfg


# ──────────────────────────────────────────────
# Wyniki
# ──────────────────────────────────────────────

VERDICT_LABELS = {
    "AC":  "Accepted",
    "WA":  "Wrong Answer",
    "TLE": "Time Limit Exceeded",
    "RE":  "Runtime Error",
    "CE":  "Compilation Error",
    "IE":  "Internal Error",
}

VERDICT_COLORS = {
    "AC":  "success",
    "WA":  "danger",
    "TLE": "warning",
    "RE":  "secondary",
    "CE":  "dark",
    "IE":  "info",
}


@dataclass
class TestResult:
    test_name: str
    verdict: str
    time_ms: float = 0.0
    points: float = 0.0
    max_points: float = 0.0
    expected_preview: str = ""
    got_preview: str = ""
    error_msg: str = ""


@dataclass
class JudgeResult:
    problem_name: str = ""
    language: str = ""
    compilation_error: str = ""
    tests: list[TestResult] = field(default_factory=list)
    total_points: float = 0.0
    max_points: float = 100.0

    @property
    def score_pct(self) -> int:
        if self.max_points == 0:
            return 0
        return round(self.total_points / self.max_points * 100)


# ──────────────────────────────────────────────
# Kompilacja
# ──────────────────────────────────────────────

class CompilationError(Exception):
    pass


def _run_cmd(cmd: list[str], cwd: Optional[str] = None) -> tuple[int, str, str]:
    """Uruchamia polecenie, zwraca (kod_wyjścia, stdout, stderr)."""
    try:
        r = subprocess.run(
            cmd, capture_output=True, text=True, cwd=cwd,
            timeout=30,
        )
        return r.returncode, r.stdout, r.stderr
    except FileNotFoundError as e:
        return -1, "", f"Nie znaleziono polecenia: {e}"
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout kompilacji"


def compile_source(source_path: Path, work_dir: Path, config: dict) -> tuple[str, list[str]]:
    """
    Kompiluje kod źródłowy.
    Zwraca (język, komenda_uruchamiająca).
    Rzuca CompilationError przy błędzie.
    """
    ext = source_path.suffix.lower()
    lang = LANGUAGE_EXTENSIONS.get(ext)
    if lang is None:
        raise CompilationError(f"Nieznane rozszerzenie pliku: {ext}")

    if lang in ("cpp", "c"):
        exe = work_dir / f"solution{EXE_SUFFIX}"
        compiler = "g++" if lang == "cpp" else "gcc"
        flags = ["-O2", "-std=c++17"] if lang == "cpp" else ["-O2"]
        rc, _, err = _run_cmd([compiler] + flags + ["-o", str(exe), str(source_path)])
        if rc != 0:
            raise CompilationError(err or "Błąd kompilacji C/C++")
        return lang, [str(exe)]

    elif lang == "python":
        py = sys.executable
        return lang, [py, str(source_path)]

    elif lang == "java":
        rc, _, err = _run_cmd(["javac", "-d", str(work_dir), str(source_path)])
        if rc != 0:
            raise CompilationError(err or "Błąd kompilacji Java")
        class_name = source_path.stem
        return lang, ["java", "-cp", str(work_dir), class_name]

    elif lang == "pascal":
        exe = work_dir / f"solution{EXE_SUFFIX}"
        rc, _, err = _run_cmd(["fpc", str(source_path), f"-o{exe}"])
        if rc != 0:
            raise CompilationError(err or "Błąd kompilacji Pascal")
        return lang, [str(exe)]

    raise CompilationError(f"Brak obsługi języka: {lang}")


# ──────────────────────────────────────────────
# Uruchamianie testów
# ──────────────────────────────────────────────

def _run_test(cmd: list[str], input_data: str, time_limit: float) -> tuple[str, float, str]:
    """Zwraca (stdout, czas_ms, błąd_lub_pusty_string)."""
    start = time.perf_counter()
    try:
        r = subprocess.run(
            cmd,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=time_limit,
        )
        elapsed = (time.perf_counter() - start) * 1000
        if r.returncode != 0:
            return r.stdout, elapsed, f"RE (kod {r.returncode}): {r.stderr[:200]}"
        return r.stdout, elapsed, ""
    except subprocess.TimeoutExpired:
        elapsed = time_limit * 1000
        return "", elapsed, "TLE"
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return "", elapsed, str(e)


def _normalize(s: str) -> str:
    """Normalizuje output do porównania (trailing spaces / newlines)."""
    lines = s.rstrip("\n").split("\n")
    return "\n".join(line.rstrip() for line in lines)


def _preview(s: str, max_chars: int = 120) -> str:
    s = s.strip()
    return s[:max_chars] + ("…" if len(s) > max_chars else "")


# ──────────────────────────────────────────────
# Główna funkcja oceniania
# ──────────────────────────────────────────────

def judge_submission(
    source_code: str,
    filename: str,
    config: dict,
    base_dir: Path,
) -> JudgeResult:
    result = JudgeResult(
        problem_name=config.get("problem_name", "Zadanie"),
    )

    in_dir  = base_dir / config["in_dir"]
    out_dir = base_dir / config["out_dir"]
    time_limit = float(config["time_limit"])

    # Zbierz testy
    test_inputs = sorted(in_dir.glob("*.in"), key=lambda p: p.stem)
    if not test_inputs:
        result.compilation_error = f"Brak plików *.in w katalogu '{in_dir}'."
        return result

    # Oblicz punkty na test
    groups: Optional[dict] = config.get("test_groups")
    points_per_test = 100.0 / len(test_inputs)

    with tempfile.TemporaryDirectory() as tmp:
        work_dir = Path(tmp)
        src_path = work_dir / filename
        src_path.write_text(source_code, encoding="utf-8")

        # Kompilacja
        try:
            lang, run_cmd = compile_source(src_path, work_dir, config)
            result.language = lang
        except CompilationError as e:
            result.compilation_error = str(e)
            result.language = LANGUAGE_EXTENSIONS.get(Path(filename).suffix.lower(), "?")
            for inp in test_inputs:
                result.tests.append(TestResult(
                    test_name=inp.stem,
                    verdict="CE",
                    max_points=points_per_test,
                ))
            result.max_points = 100.0
            return result

        # Uruchom każdy test
        for inp in test_inputs:
            out_path = out_dir / (inp.stem + ".out")
            test_name = inp.stem

            if not out_path.exists():
                result.tests.append(TestResult(
                    test_name=test_name,
                    verdict="IE",
                    max_points=points_per_test,
                    error_msg=f"Brak pliku wyjściowego: {out_path.name}",
                ))
                continue

            try:
                expected = out_path.read_text(encoding="utf-8")
            except Exception as e:
                result.tests.append(TestResult(
                    test_name=test_name,
                    verdict="IE",
                    max_points=points_per_test,
                    error_msg=f"Błąd odczytu pliku wyjściowego: {e}",
                ))
                continue

            input_data = inp.read_text(encoding="utf-8")
            got, elapsed_ms, error = _run_test(run_cmd, input_data, time_limit)

            if error == "TLE":
                verdict = "TLE"
            elif error.startswith("RE"):
                verdict = "RE"
            elif error:
                verdict = "RE"
            elif _normalize(got) == _normalize(expected):
                verdict = "AC"
            else:
                verdict = "WA"

            pts = points_per_test if verdict == "AC" else 0.0

            result.tests.append(TestResult(
                test_name=test_name,
                verdict=verdict,
                time_ms=round(elapsed_ms, 1),
                points=pts,
                max_points=points_per_test,
                expected_preview=_preview(expected) if verdict == "WA" else "",
                got_preview=_preview(got) if verdict in ("WA", "RE") else "",
                error_msg=error if verdict not in ("AC", "WA") else "",
            ))

    result.total_points = sum(t.points for t in result.tests)
    result.max_points   = sum(t.max_points for t in result.tests)
    return result
