# Delikatna poprawa oświetlenia dekoracji boisk

`authoring/polish_map_normals.py` odtwarza dwie miejscowe poprawki beta3 na
podstawie dokładnych plików moda beta2. Narzędzie jest autorskim kodem objętym
licencją MIT repozytorium. Korzysta wyłącznie ze standardowej biblioteki Pythona;
nie wymaga Blendera, Pillow, modeli AI ani uruchamiania silnika gry.

W tym przepisie nie ma modeli, tekstur, oryginalnych klas gry ani innych
materiałów źródłowych. Prawa do zasobów gier pozostają opisane w
[THIRD_PARTY.md](../THIRD_PARTY.md). Nazwy plików i materiałów poniżej służą
identyfikacji zgodnych wejść.

## Użycie

Wejściem jest własna instalacja moda **beta2** lub odtworzony lokalnie payload
tej wersji. Czysta bazowa gra nie zawiera dodatkowych boisk wymaganych przez
ten przepis. Narzędzie wymaga dokładnych hashy dwóch wejściowych siatek i
odmawia pracy na innej wersji, w tym już poprawionej beta3.

Uruchom z głównego katalogu repozytorium:

```powershell
python authoring/polish_map_normals.py --source 'C:/Gry/PetSoccerGMW-beta2' --output 'build/map-normal-polish'
```

Wynik powstaje w nowym, osobnym katalogu. Wejście i wyjście muszą być rozłączne;
istniejące wyniki nie są nadpisywane. Oba wejścia są sprawdzane i obliczane przed
zapisem. Wynik zawiera tylko dwie poprawione siatki w ich ścieżkach `Data/` i
raport `manifest.json`. Samo uruchomienie przepisu nie instaluje ich w grze.

Przetestowano dokładne odtworzenie bajtów na CPython 3.13. Narzędzie sprawdza
również oczekiwany hash wyniku; ewentualna różnica obliczeń na innym środowisku
kończy się błędem przed zapisem, zamiast tworzyć niezweryfikowany wariant.
Kontrole pozostają aktywne przy `python -O`.

## Dokładny zakres

Zmieniają się wyłącznie wybrane zapisane wektory normalne powierzchni:

| Boisko | Zmienione normalne | Materiały |
| --- | ---: | --- |
| Old Camp, siatka 38 | 2180 | `cx38_crag.png` |
| Kaer Morhen, siatka 40 | 12703 | `cx40v2_cliff.png`, `cx40v2_clifftop.png`, `cx40v2_leaf.png`, `cx40v2_leaflit.png` |

Przepis łączy tylko sąsiednie trójkąty o tym samym materiale, połączone wspólną
krawędzią z dokładnie dwiema ścianami. Sama zgodność pojedynczej pozycji nie
łączy niezależnych powierzchni. Załamania ponad 55 stopni pozostają ostre.
Docelowa normalna wynika ze średniej ważonej polem ścian w połączonym wachlarzu,
a wynik stanowi mieszankę 55% nowej i 45% dotychczasowej normalnej.

Przy bardzo ostrych czubkach, niejednoznacznych wachlarzach lub wierzchołkach
współdzielonych z innym materiałem normalna pozostaje bez zmiany. Istniejące
trójkąty o zerowej powierzchni są zachowane. Największy obrót normalnej wynosi
około 19,31 stopnia; wszystkie wynikowe wektory pozostają skończone i jednostkowe.

Pozycje, liczba wierzchołków i trójkątów, indeksy oraz kolejność ścian, UV,
przypisania materiałów, hierarchia, ścieżki animacji, obrysy i rozmiary plików są
bajtowo identyczne. Narzędzie nie dotyka tekstur, architektury, boiska Minecraft,
oryginalnych boisk, plików MAP, wysokości PS_H, statycznego cieniowania PS_S,
oznaczeń piłkarskich, punktów startu ani kolizji. Nie wykonuje upscalingu.

Liczba prymitywów i rozmiary tekstur pozostają takie same, więc ten przepis
nie dodaje geometrii ani pamięci tekstur. Nie jest to pomiar FPS ani deklaracja
przyspieszenia gry.

## Wejścia i wyniki

| Plik | SHA256 beta2 | SHA256 beta3 |
| --- | --- | --- |
| `Data/Meshes/Objects/CXarena38.3da` | `da867fc8b33a5c092010f558e5ccb427894d05bbba6b89c49c54aec1c1e94a11` | `07841d048ab26c9b4d3c99ef0435a1a79e353d3fa404bbbb0b699f0d38fc8ddb` |
| `Data/Meshes/Objects/CXarena40.3da` | `73e1afc05c31ffad83e55a3545cb1d97bc085f012780635e3d9388a6988bbfb7` | `f08884fe7b511568b2120ff14da23c75559e666ff04820260cb7f6b4cbedbf6e` |

## Pochodzenie i sprawdzenie przepisu

To przenośny, uporządkowany eksport autorskiego narzędzia użytego do tej
konkretnej poprawki. Zachowuje jego obliczenia i wynikowe bajty, dodając jawne
kontrole również dla zoptymalizowanego uruchomienia Pythona, walidację obu wejść
przed zapisem, kontrolę oczekiwanych wyników oraz raport bez prywatnych ścieżek.
Nie odtwarza dawnych generatorów całych map nad późniejszymi poprawkami.

Odtworzenie obu wyników w pamięci dało dokładne, zaakceptowane do integracji
pliki beta3. Oddzielny audyt zakresów bajtów potwierdził ograniczenie zmian do
normalnych, a recenzent obejrzał porównywalne rendery przed/po obu siatek przy
wspólnym kadrze i oświetleniu. To potwierdza zgodność danych i kierunek zmiany
w renderze offline. Wynik nie jest automatycznie testem wyglądu, stabilności ani
wydajności w natywnym silniku Pet Soccer.

Osobno sprawdzano odziedziczone cienie drzew w PS_S. Ze względu na mieszane
cieniowanie terenu i brak pewnego rozdzielenia masek **nie zmieniono tej warstwy**.
Ten przepis nie zawiera naprawy statycznych cieni ani nowych tekstur murawy.
