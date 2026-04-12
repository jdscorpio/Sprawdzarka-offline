#!/usr/bin/env python3
"""
Narzędzie pomocnicze – zarządzanie plikami wyjściowymi.

Użycie:
  python encrypt_tool.py status         – sprawdza stan plików in/out
  python encrypt_tool.py run <program>  – generuje pliki .out uruchamiając wzorcowe rozwiązanie
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich import box

from judge_core import load_config, LANGUAGE_EXTENSIONS

console = Console()


def show_status(config: dict, base_dir: Path) -> None:
    in_dir  = base_dir / config["in_dir"]
    out_dir = base_dir / config["out_dir"]

    inputs = sorted(in_dir.glob("*.in"))
    table = Table(title="Stan plików testowych", box=box.ROUNDED, show_lines=True)
    table.add_column("Test", style="bold cyan", justify="center")
    table.add_column("Plik .in", justify="center")
    table.add_column("Plik .out", justify="center")

    for inp in inputs:
        out = out_dir / (inp.stem + ".out")
        out_ok = "[green]✓[/]" if out.exists() else "[red]BRAK[/]"
        table.add_row(inp.stem, "[green]✓[/]", out_ok)

    console.print(table)


def run_and_save(solution_path: str, config: dict, base_dir: Path) -> None:
    src = Path(solution_path)
    if not src.exists():
        console.print(f"[red]Nie znaleziono pliku: {solution_path}[/]")
        sys.exit(1)

    in_dir  = base_dir / config["in_dir"]
    out_dir = base_dir / config["out_dir"]

    ext  = src.suffix.lower()
    lang = LANGUAGE_EXTENSIONS.get(ext)
    if lang is None:
        console.print(f"[red]Nieobsługiwane rozszerzenie: {ext}[/]")
        sys.exit(1)

    if lang == "python":
        run_cmd = [sys.executable, str(src)]
        console.print(f"[cyan]Język: Python (bez kompilacji)[/]")
        _generate_outputs(run_cmd, in_dir, out_dir, config)
        return

    if lang in ("cpp", "c"):
        import tempfile, platform
        exe_suf = ".exe" if platform.system() == "Windows" else ""
        tmp_dir = Path(tempfile.mkdtemp())
        exe = tmp_dir / f"wzorzec{exe_suf}"
        compiler = "g++" if lang == "cpp" else "gcc"
        flags = ["-O2", "-std=c++17"] if lang == "cpp" else ["-O2"]
        r = subprocess.run(
            [compiler] + flags + ["-o", str(exe), str(src)],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            console.print(f"[red]Błąd kompilacji:\n{r.stderr}[/]")
            sys.exit(1)
        console.print(f"[cyan]Skompilowano {src.name}[/]")
        _generate_outputs([str(exe)], in_dir, out_dir, config)
        return

    if lang == "java":
        import tempfile
        tmp_dir = Path(tempfile.mkdtemp())
        r = subprocess.run(["javac", "-d", str(tmp_dir), str(src)], capture_output=True, text=True)
        if r.returncode != 0:
            console.print(f"[red]Błąd kompilacji Java:\n{r.stderr}[/]")
            sys.exit(1)
        _generate_outputs(["java", "-cp", str(tmp_dir), src.stem], in_dir, out_dir, config)
        return

    console.print(f"[red]Nieobsługiwany język: {lang}[/]")
    sys.exit(1)


def _generate_outputs(exe_cmd: list, in_dir: Path, out_dir: Path, config: dict) -> None:
    inputs = sorted(in_dir.glob("*.in"))
    if not inputs:
        console.print("[yellow]Brak plików *.in[/]")
        return

    time_limit = float(config.get("time_limit", 10.0)) * 3
    ok = 0
    for inp in inputs:
        input_data = inp.read_text(encoding="utf-8")
        try:
            r = subprocess.run(
                exe_cmd, input=input_data, capture_output=True, text=True,
                timeout=time_limit,
            )
            if r.returncode != 0:
                console.print(f"  [red]✗[/] {inp.name}  – błąd wykonania: {r.stderr[:80]}")
                continue
            output = r.stdout
        except subprocess.TimeoutExpired:
            console.print(f"  [red]✗[/] {inp.name}  – timeout wzorca")
            continue

        out_path = out_dir / (inp.stem + ".out")
        out_path.write_text(output, encoding="utf-8")
        console.print(f"  [green]✓[/] {inp.name}  →  {out_path.name}")
        ok += 1

    console.print(f"\n[bold green]Wygenerowano {ok}/{len(inputs)} plików.[/]")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Narzędzie do zarządzania plikami wyjściowymi.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("status", help="Sprawdza stan plików")
    run_p = sub.add_parser("run", help="Generuje pliki .out z wzorcowego rozwiązania")
    run_p.add_argument("solution", help="Ścieżka do wzorcowego rozwiązania")

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        sys.exit(0)

    base_dir = Path(__file__).parent
    config = load_config(str(base_dir / "zadanie" / "config.json"))

    console.rule("[bold blue]Sprawdzarka Offline – Narzędzie[/]")

    if args.cmd == "status":
        show_status(config, base_dir)
    elif args.cmd == "run":
        run_and_save(args.solution, config, base_dir)


if __name__ == "__main__":
    main()
