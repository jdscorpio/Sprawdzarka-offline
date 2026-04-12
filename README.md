# Sprawdzarka Offline

Lokalny sędzia (offline judge) z interfejsem webowym.
Użytkownik wkleja lub wgrywa kod źródłowy i otrzymuje informację, które testy przeszły, a które nie, wraz z przyznaną liczbą punktów (max 100).

---

## Szybki start

### 1. Zainstaluj zależności

```
pip install -r requirements.txt
```

### 2. Uruchom setup demonstracyjny (pierwsze uruchomienie)

Generuje pliki wyjściowe dla przykładowego zadania (suma dwóch liczb):

```
python setup_demo.py
```

### 3. Uruchom aplikację

```
python app.py
```

Otwórz przeglądarkę pod adresem: **http://localhost:5000**

---

## Struktura projektu

```
Sprawdzarka offline/
├── app.py              – serwer Flask (interfejs webowy)
├── judge_core.py       – silnik oceniania (kompilacja, uruchamianie, porównywanie)
├── encrypt_tool.py     – narzędzie CLI do zarządzania plikami .out
├── setup_demo.py       – skrypt generujący przykładowe pliki wyjściowe
├── config.json         – konfiguracja (limit czasu, itp.)
├── requirements.txt    – zależności Pythona
├── templates/
│   └── index.html      – interfejs webowy (CodeMirror + Bootstrap)
└── zadanie/
    ├── treść.pdf       – (opcjonalnie) treść zadania – wyświetlana w aplikacji
    ├── in/             – pliki wejściowe testów (*.in)
    └── out/            – pliki wyjściowe testów (*.out)
```

---

## Obsługiwane języki

| Język    | Rozszerzenie | Wymagany kompilator |
|----------|-------------|---------------------|
| C++      | .cpp        | `g++` (MinGW / GCC) |
| C        | .c          | `gcc`               |
| Python 3 | .py         | Python w PATH       |
| Java     | .java       | `javac` + `java`    |
| Pascal   | .pas        | `fpc` (Free Pascal) |

---

## Konfiguracja (`config.json`)

```json
{
    "time_limit": 2.0,       // limit czasu w sekundach
    "memory_limit": 256,     // informacyjnie (nieegzekwowane na Windows)
    "in_dir": "in",          // folder z plikami .in
    "out_dir": "out",        // folder z plikami .out
    "problem_name": "Nazwa zadania"
}
```

---

## Dodawanie własnych zadań

### Metoda A – ręcznie

1. Umieść pliki wejściowe w `zadanie/in/` (np. `1.in`, `2.in`, …)
2. Umieść odpowiedzi w `zadanie/out/` jako `1.out`, `2.out`, …
3. (Opcjonalnie) Umieść plik PDF z treścią w `zadanie/` — zostanie automatycznie wykryty i wyświetlony w aplikacji
4. Uruchom `python app.py`

### Metoda B – z wzorcowego rozwiązania

1. Umieść pliki `.in` w `zadanie/in/`
2. Wygeneruj pliki `.out` automatycznie:
   ```
   python encrypt_tool.py run wzorzec.cpp
   ```

## Treść zadania (PDF)

Jeśli w folderze `zadanie/` umieścisz plik `.pdf`, w górnym pasku aplikacji pojawi się przycisk **Treść zadania**. Po kliknięciu otwiera się podgląd PDF bezpośrednio w przeglądarce, z opcją otwarcia w nowej karcie lub pobrania.

---

## Narzędzie pomocnicze (`encrypt_tool.py`)

```
python encrypt_tool.py status          – sprawdza stan plików testowych
python encrypt_tool.py run <plik>      – generuje .out z wzorcowego rozwiązania
```

---

## Skróty klawiszowe (interfejs webowy)

| Skrót         | Akcja    |
|---------------|----------|
| `Ctrl+Enter`  | Oceń kod |
| `Tab`         | 4 spacje |

---

## Werdykty

| Symbol | Znaczenie                    |
|--------|------------------------------|
| AC     | Accepted (poprawny)          |
| WA     | Wrong Answer (zła odpowiedź) |
| TLE    | Time Limit Exceeded          |
| RE     | Runtime Error                |
| CE     | Compilation Error            |
| IE     | Internal Error (brak .out)   |

---

## Punktacja

Każdy test jest wart równą część ze 100 punktów.  
Wynik końcowy = (liczba_AC / liczba_testów) × 100, zaokrąglone do liczby całkowitej.
