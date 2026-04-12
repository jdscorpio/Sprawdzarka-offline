#!/usr/bin/env python3
"""
Skrypt konfiguracyjny – generuje pliki wyjściowe dla przykładowego zadania.

Przykładowe zadanie: Dana jest para liczb całkowitych a i b.
Wypisz ich sumę.

Uruchom raz, żeby przygotować środowisko:
  python setup_demo.py
"""

from pathlib import Path
from judge_core import load_config

BASE_DIR = Path(__file__).parent
config   = load_config(str(BASE_DIR / "zadanie" / "config.json"))

out_dir = BASE_DIR / config["out_dir"]
in_dir  = BASE_DIR / config["in_dir"]
out_dir.mkdir(exist_ok=True)


def wzorzec(input_text: str) -> str:
    a, b = map(int, input_text.strip().split())
    return str(a + b) + "\n"


print("=" * 50)
print("  Setup – generowanie plików wyjściowych")
print("=" * 50)

inputs = sorted(in_dir.glob("*.in"))
if not inputs:
    print("[BŁĄD] Brak plików *.in w katalogu 'in/'")
    exit(1)

for inp in inputs:
    text     = inp.read_text(encoding="utf-8")
    answer   = wzorzec(text)
    out_path = out_dir / (inp.stem + ".out")
    out_path.write_text(answer, encoding="utf-8")
    print(f"  ✓  {inp.name}  →  {out_path.name}  (wynik: {answer.strip()})")

print()
print(f"Wygenerowano {len(inputs)} plików wyjściowych.")
print()
print("Możesz teraz uruchomić aplikację:")
print("  python app.py")
print()
print("Przykładowe poprawne rozwiązanie (C++):")
print("  #include <bits/stdc++.h>")
print("  using namespace std;")
print("  int main() {")
print("      long long a, b;")
print("      cin >> a >> b;")
print("      cout << a + b << endl;")
print("      return 0;")
print("  }")
