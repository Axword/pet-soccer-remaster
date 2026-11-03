# Modele, animacje i mapy

Przenośne źródła nowych wariantów zwierząt, map bazowych, Jagniellonii i końcowej
naprawy oczu dla wersji Online beta 1: [features/README.md](features/README.md).
Te przepisy przyjmują jawne ścieżki wejściowe i wyjściowe; nie wymagają historycznego
układu lokalnych katalogów. Wszystkie źródłowe assety trzeba dostarczyć osobno.

Aktualna naprawa ubrań Wiedźmina: [WITCHER_CLOTHING_REPAIR.md](../docs/WITCHER_CLOTHING_REPAIR.md).
Odtwarza brakujące powierzchnie z lokalnych autentycznych modeli i zachowuje
bieżący szkielet, animacje oraz atlasy. Historyczny przepis upraszczania rozłączonych
wysp UV usuwał fragmenty ubrań; do bieżącej paczki stosuj nowy, sprawdzony przepis.
Delikatne wygładzenie map opisuje [MAP_NORMAL_POLISH.md](../docs/MAP_NORMAL_POLISH.md).

`recipes` zawiera24 rzeczywiste autorskie skrypty używane podczas adaptacji
modeli, eksportu formatu3DA0x101, naprawy animacji Gothic/Wiedźmina, skalowania,
budowy map i powiększania tekstur Minecraft. To kod prac nad assetami, a nie
źródła modeli z innych gier.

Skrypty zachowują historyczny układ folderów i założenia wejść. Zostały
zabezpieczone przed przypadkowym uruchomieniem bezpośrednio w repozytorium lub
nad zainstalowaną grą. Nie stanowią jednego automatycznego procesu odtwarzającego
każdą zaakceptowaną ręczną poprawkę modeli.

## Izolowane środowisko

```powershell
python tools/prepare_authoring.py --base-game 'C:\Gry\Pet Soccer'
```

Narzędzie kopiuje tylko źródła skryptów oraz opcjonalny oryginalny model/INI
robota potrzebny jako lokalna referencja rig-u do `build/authoring`.
Nie kopiuje pełnej gry ani nie uruchamia jej. Blender i dodatkowe biblioteki
pozostają zewnętrznymi zależnościami.

Po przygotowaniu wejść można jawnie uruchomić wybrany skrypt:

```powershell
python tools/prepare_authoring.py --base-game 'C:\Gry\Pet Soccer' --gothic-game 'C:\Gry\Gothic' --recipe remaster/factions/build_gothic.py --blender 'C:\Blender\blender.exe' --run
```

`--run` uruchamia Blender w tle, nie silnik Pet Soccer. Własne źródłowe modele,
tekstury, JSON-y szkieletu, klipy MAN i porty Workshop należy przygotować lokalnie
w układzie odczytywanym przez dany przepis. Brakujący plik jest błędem wejścia;
nie pobieramy ani nie dołączamy oryginalnych archiwów innych gier.

Zależnie od przepisu potrzebne są `mathutils`/Blender, Pillow, NumPy, ZenKit
lub SourceIO. Te projekty zachowują własne licencje i nie są vendoryzowane tutaj.
Identyfikatory portów postaci Wiedźmina są jawne w przepisie i w danych rosterów.

## Bezpośrednia edycja paczki

Do pracy na już przygotowanych atlasach można użyć prostszego, przenośnego
narzędzia (wymaga Pillow):

```powershell
python authoring/upscale_minecraft.py --input package/payload/Data/Textures --output build/upscaled
```

Używa wyłącznie całkowitego skalowania nearest-neighbour i sprawdza dokładny
powrót do oryginalnych pikseli. Nie nadpisuje wejść ani istniejących wyników.

Zmiana geometrii lub animacji wymaga obejrzenia modelu z przodu/boku i w meczu.
Zachowanie długości osi czasu nie potwierdza braku wpływu na zaczepy piłki,
zasięgi lub collider. Pliki `build` i zewnętrzne materiały źródłowe są ignorowane
przez Git; nie dodawaj ich do repozytorium.
