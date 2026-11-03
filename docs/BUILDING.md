# Budowanie i rozwój

Wszystkie wejścia oryginalnej gry pozostają lokalne. Nie dodawaj ich do Git.
Do testów stosuj nowy folder roboczy; narzędzia nie powinny nadpisywać oryginału.

## Bieżące wydanie Online 0.2.0-beta.1

Dla nowej wersji stosuj kolejność opisaną w [ONLINE.md](ONLINE.md) i narzędzie
`tools/build_online.py`. Ono wybiera odpowiednie klasy i nakłada przepisy
rejestracji Jagniellonii. Poniższe przykłady beta3 są dokumentacją historycznych
etapów: hurtowa podmiana wszystkich klas po zbudowaniu Online odpięłaby część
nowych hooków. Pochodzenie bieżących źródeł: [SOURCE_PROVENANCE.md](SOURCE_PROVENANCE.md).

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

## Referencyjne odtworzenie beta3

Wejściem obu przepisów jest właściwy etap **beta2**. Każdy wynik powstaje w
nowym katalogu; nie nakładaj generatorów na aktualną instalację ani ręcznie
poprawione modele. Nazwy ścieżek poniżej są przykładami lokalnych wejść:

```powershell
$originalGame = 'C:/Gry/Pet Soccer'
$beta2Code = 'C:/Gry/PetSoccerGMW-beta2/code.pak'
$beta2Index = 'C:/Gry/PetSoccerGMW-beta2/code_inf.pak'
$ecj = 'tools/external/ecj-3.7.2.jar'

python tools/compile_java.py --game "$originalGame" --classpath "$beta2Code" --ecj "$ecj"
python -m src.patches.human_preview --input "$beta2Code" --code-index "$beta2Index" --helper build/java/CXHumanPreview.class --output build/beta3-preview
python -m src.patches.preview_text --code build/beta3-preview/code.pak --code-index build/beta3-preview/code_inf.pak --helper build/java/CXPreviewText.class --output build/beta3-code
```

Przepisy sprawdzają odciski metod i odrzucają niezgodne lub już zmienione
wejście. Finalne archiwum i indeks pochodzą z `build/beta3-code/`.
Dla zamrożonego wejścia referencyjnego odtworzono dokładny SHA archiwum
`82cf7b366d8c54d5f99368ad4c34301bf077f26666c277f94f8753bf17a051f5`
oraz indeksu
`ef5d1c392976f6a5f0bd31bf2239c69e5ef798dfc26a072164f4dc87e512ef04`.
To 431 wpisów ZIP, w tym 429 klas. Inny układ metadanych/kompresji ZIP może
zmienić hash całego archiwum; zgodność klas i normalizację sprawdzają narzędzia
paczki. Pełne archiwa wynikowe pozostają lokalnymi plikami roboczymi.

Geometrię odtwarzaj oddzielnie. Dwie miejscowe poprawki normalnych opisuje
[MAP_NORMAL_POLISH.md](MAP_NORMAL_POLISH.md). Autorskie narzędzia
`authoring/read_witcher_clothing.py` i `authoring/restore_witcher_clothing.py`
wraz z `authoring/witcher-clothing-contract.json` wymagają lokalnych źródeł
MDL/VVD/DX90VTX, SourceIO oraz Blendera/Pythona z NumPy. Pośrednie NPZ są
prywatne. Dokładna kolejność i wejścia:
[WITCHER_CLOTHING_REPAIR.md](WITCHER_CLOTHING_REPAIR.md).
Te narzędzia przywracają wybrane części do bieżącego rigu; nie służą do
regenerowania całej gry ze starego snapshotu.

Stan oraz ograniczenia odbioru beta3 znajdują się w [BETA3.md](BETA3.md).

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

Siedem testów przepisu podglądów wymaga własnego lokalnego wejścia beta2 oraz
skompilowanego helpera. W PowerShell, przed uruchomieniem powyższej komendy:

```powershell
$env:PET_SOCCER_CODE_PAK = $beta2Code
$env:PET_SOCCER_PREVIEW_HELPER = (Resolve-Path 'build/java/CXHumanPreview.class').Path
```

W przygotowaniu beta3 przeszło 15 publicznych testów Python. Oddzielne 1164
prywatne asercje JVM sprawdzały poprawione klasy menu z jawnymi atrapami
natywnego schedulera, ładowania siatek i renderera. Prywatne klasy/sterowniki QA
nie trafiają do repozytorium ani instalatora; tych wyników nie traktuje się
jako testu wyglądu, FPS lub pełnego meczu w natywnym silniku.

Testy reguł Java wykorzystują własne klasy moda i jawne atrapy granic silnika;
nie są testem renderera. `BuildCleanSave.java` sprawdza tworzenie i odczyt
czystego zapisu przy użyciu lokalnych klas serializatora gry.

Przed wydaniem sprawdź kompilację, odtworzenie wszystkich plików z manifestu,
cichy test instalacji/odinstalowania oraz faktyczny mecz z oboma padami.
Samo odczytanie źródeł nie potwierdza działania w silniku.

