# Budowanie i rozwój

Wszystkie wejścia oryginalnej gry pozostają lokalne. Nie dodawaj ich do Git.
Do testów stosuj nowy folder roboczy; narzędzia nie powinny nadpisywać oryginału.

## Wymagania

- Windows, Python3.10+.
- MSVC z narzędziami x86 i Windows SDK.
- Zewnętrzne nagłówki JNI z JDK (`JAVA_HOME`, `include` i `include/win32`).
- Oryginalna polska instalacja Pet Soccer, wraz z jej środowiskiem Java1.3.
- Zewnętrzny Eclipse ECJ wspierający `-source1.3 -target1.3`, np.3.7.2.
- NSIS do zbudowania instalatora.

Nagłówki JDK, kompilatory i środowisko gry nie są vendoryzowane w repozytorium.
Pobierz je z odpowiednich oficjalnych źródeł i zachowaj ich warunki licencyjne.

## Mostek C++

```powershell
$env:JAVA_HOME = 'C:\ścieżka\do\jdk'
python tools/build_native.py
```

Można również wskazać katalog zawierający `jni.h` i `jni_md.h` przez `--jni-dir`.
Narzędzie wykrywa MSVC przez `vswhere` i buduje x86 w `build/native`.
Gotową bibliotekę podstawiaj tylko do lokalnej kopii testowej moda.

## Własne klasy Java

Najpierw odtwórz lokalną kopię moda z wydania beta. Następnie skompiluj klasy
przeciwko jej `code.pak`; sam PAK nie trafia do repozytorium:

```powershell
python tools/compile_java.py --game 'C:\Gry\Pet Soccer' --classpath 'C:\Gry\PetSoccerGMW\code.pak' --ecj 'tools\external\ecj-3.7.2.jar'
python tools/replace_classes.py --input 'C:\Gry\PetSoccerGMW\code.pak' --classes build/java --output build/patched-code.pak
```

Wynik Java musi pozostać zgodny z1.3 (major47). `replace_classes.py` tworzy nowy
plik, zachowując pozostałe wpisy archiwum; nie uruchamia silnika ani nie
kopiuje wyniku do zainstalowanej gry.

## Przepisy zmian bajtkodu

```powershell
python tools/apply_recipe.py timing --input build/reference-code.pak --output build/timed-code.pak
```

Każdy przepis wymaga wejścia właściwego dla danego etapu. `timing` sprawdza
odciski zmienianych metod. `bracket` i `gmw_profile` przyjmują dodatkowo
`--baseline` wskazujący dokładny stan sprzed tego etapu oraz `--compiled`
z odpowiednimi własnymi klasami. Tablice profilu przekazuje `--snapshot`.
Jeżeli odcisk/metoda się nie zgadza, przerwij i zrób nowy audyt zamiast usuwać
asercje. Te przepisy nie są zamiennikiem całego historycznego procesu ekstrakcji
i adaptacji modeli z innych gier.

## Instalator i pliki paczki

Do odtworzenia instalatora z już opublikowanych plików paczki wystarczą MSVCx86
i NSIS. Poniższa komenda buduje własny backend i kompiluje instalator; nie
uruchamia go ani nie kopiuje gry:

```powershell
./build_installer.ps1 -NsisCompiler 'C:\NSIS\makensis.exe'
```

Wynik powstaje w ignorowanym `release`. Źródło formatu łat i niezależny dekoder
to `delta.py` oraz `installer/delta_format.h`; specyfikacja:
[DELTA_FORMAT.md](DELTA_FORMAT.md).

Ponowne generowanie plików paczki, np. po zmianie klas lub modeli, odbywa się
przez `build_public_package.py --base-game ... --mod-profile ... --output ...`.
To polecenie wymaga oryginalnego folderu bazowego oraz zweryfikowanej lokalnej
kopii profilu moda. Katalog `--mod-profile` zawiera `payload/` i `payload.tsv`
z całkowitymi lokalnymi wynikami sprzed przekształcenia na publiczne łatki.
Nie jest dołączany do repozytorium; w repozytorium są już wynikowe pliki paczki.
Pliki istniejące już w oryginale mają być pominięte lub zamienione na łatkę,
a nie publikowane jako pełne pliki. Archiwum klas wymaga normalizacji ZIP,
aby niezmienione klasy były kopiowane z lokalnej gry, zamiast przypadkowo
trafiać do literalnej części łatki przez inne parametry kompresji.

Nie uruchamiaj dawnych generatorów nad nowymi ustawieniami i ręcznie
poprawionymi modelami. Wydanie używa zamrożonego manifestu plików.

## Testy

```powershell
python -m unittest discover -s tests -p 'test_*.py'
```

Testy reguł Java wykorzystują własne klasy moda i jawne atrapy granic silnika;
nie są testem renderera. `BuildCleanSave.java` sprawdza tworzenie i odczyt
czystego zapisu przy użyciu lokalnych klas serializatora gry.

Przed wydaniem sprawdź kompilację, odtworzenie wszystkich plików z manifestu,
cichy test instalacji/odinstalowania oraz faktyczny mecz z oboma padami.
Samo odczytanie źródeł nie potwierdza działania w silniku.

