# Budowanie i testowanie własnego Online

Kod serwera i launchera znajduje się w `src/online`. Katalog zawiera wyłącznie
własne źródła, testy, skrypty oraz odciski oficjalnego środowiska Python.
Nie powiela binariów tego środowiska z `package/payload/online/runtime`.
Wszystkie wyniki poniższych poleceń powstają w ignorowanym przez Git `build/`.
Nie wymagają oryginalnej gry, Blendera, Java ani uruchomienia renderera.

Wymagania budowania: Windows10/11, Python3.10+ do uruchomienia narzędzi,
MSVC z narzędziami C++ x86 i Windows SDK (`vswhere` wykrywa kompilator).
Można jawnie podać `--vcvars C:/narzedzia/vcvars32.bat` przy budowie launchera.
Testy wymagają zewnętrznego MSVC również do kompilacji małych programów
sprawdzających. Narzędzia nie instalują kompilatora ani pakietów pip.

## Nowy workspace z istniejącym pakietem

Po czystym checkout źródeł wraz z publicznym katalogiem `package`:

```powershell
python tools/prepare_online_workspace.py --workspace build/online --runtime-dir package/payload/online/runtime
python tools/build_online_launcher.py --workspace build/online
python tools/test_online.py --workspace build/online --suite all
```

`prepare_online_workspace.py` odmawia nadpisania istniejącego katalogu.
Wybierz nową nazwę, jeżeli chcesz zachować poprzedni build lub lokalny ranking.
Workspace musi rozwiązywać się do podkatalogu `build/` tego checkoutu;
wyjście poza checkout przez symlink/junction również jest odrzucane.

## Nowy workspace z oficjalnym archiwum

Jeżeli nie masz gotowego runtime z wydania, pobierz oficjalny
[CPython3.14.10 embeddable win32](https://www.python.org/ftp/python/3.14.10/python-3.14.10-embed-win32.zip).
Zachowaj archiwum poza śledzonymi plikami repozytorium, np. w `build/downloads`.

```powershell
python tools/prepare_online_workspace.py --workspace build/online
python tools/build_online_runtime.py --workspace build/online --archive build/downloads/python-3.14.10-embed-win32.zip
python tools/build_online_launcher.py --workspace build/online
python tools/test_online.py --workspace build/online --suite all
```

Narzędzie sprawdza SHA256 całego archiwum:
`11a28e8c00a6d8f56b0a6164d52546133a9ed015a5b33e04536917e4fd6e306c`.
Następnie sprawdza pełny zestaw36 plików, rozmiary oraz indywidualne SHA256
według `src/online/runtime-contract.json`. Wariant `--runtime-dir` przechodzi
takie same indywidualne kontrole. Nic nie jest przycinane ani podmieniane;
`LICENSE.txt`, biblioteka standardowa, SQLite i biblioteki DLL pozostają razem.
Weryfikacja odbywa się przed zapisaniem nowego katalogu runtime.

## Wyniki i testy

Launcher powstaje w `build/online/payload/PetSoccer-Online.exe`, jego obiekty
i dziennik kompilacji w `build/online/build/`. Gotowa paczka instalacyjna
umieszcza go obok rekonstruowanego `PetSoccer.exe`, nie w podkatalogu gry.
Samo zbudowanie źródeł Online nie dostarcza oryginalnego silnika gry.

Testy można wykonać osobno:

```powershell
python tools/test_online.py --workspace build/online --suite protocol
python tools/test_online.py --workspace build/online --suite guard
```

Pierwsza grupa to48 testów konsolowych transportu, pokoi, rankingu, pauzy,
gatunku58 i sprawdzania odpowiedzi serwera przez launcher. Używa rzeczywiście
dołączonego interpretera z workspace, tymczasowych baz i portów loopback.
Wynik oraz log zapisuje w `build/online/test-results.json` i `test-results.log`.

Druga grupa to15 sprawdzeń przed podwójnym startem. Uruchamia małe własne
programy o nazwach `PetSoccer.exe`/`PetSoccer.bum` wyłącznie w katalogach
testowych; nie są grą i nie otwierają renderera. Sprawdza m.in. jednoczesne
kliknięcia, przejście bootstrap→engine, dokładną ścieżkę obrazu i oddzielne
instalacje. Wynik jest w `build/online/tests/guard-evidence/results.json`.

Opcjonalny sprawdzian rzeczywistego CLI serwera i tej samej funkcji C++
sprawdzającej gotowość:

```powershell
build/online/payload/online/runtime/python.exe -I -B build/online/tests/real_broker_probe.py
```

Tworzy własny proces serwera na tymczasowym porcie oraz własną bazę, po czym
zamyka wyłącznie swój proces. Nie dotyka portów produkcyjnych27888/27889.
Żaden z tych testów nie uruchamia gry ani nie zmienia zapory lub zapisów.

## Co jest publikowane

- `src/online/online_launcher.cpp` — pełne źródło własnego launchera.
- `src/online/broker.py` — pełny własny serwer; domyślnie CLI kopii źródłowej
  jest zablokowane znacznikiem `SOURCE_ONLY.md`, aby nie tworzyć bazy w `src`.
  Workspace kopiuje broker bez tego znacznika; logika protokołu jest ta sama.
- `src/online/tests` — własne testy Python i C++, bez plików wykonywalnych.
- `src/online/scripts` — skrypty LAN, połączenia z własnym serwerem i jawnego
  zatrzymania lobby tej instalacji. Testy ich nie wykonują na rzeczywistych usługach.
- `src/online/workspace_*` — własne moduły budujące/testujące kopiowane do
  workspace; bez znacznika workspace odmawiają zapisu wyników.

Szczegóły protokołu zawiera [PROTOCOL.md](../src/online/PROTOCOL.md), a użycie
gry oraz zakres dotychczasowych testów — [ONLINE.md](ONLINE.md).
Kompilacja i testy konsolowe nie są dowodem działania Internetu na dwóch
komputerach ani gwarancją stabilności wszystkich map starego silnika.
