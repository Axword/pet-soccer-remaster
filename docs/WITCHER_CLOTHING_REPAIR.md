# Odtwarzanie powierzchni ubrań Wiedźmina

Ten przepis zawiera autorski kod odczytu i naprawy adapterów oraz tabele
zgodności wejść. Nie zawiera oryginalnych MDL/VVD/VTX, SourceIO, siatek, tekstur
ani pośrednich tablic geometrii NPZ. Licencja MIT repozytorium obejmuje własny
kod i dokumentację; nie zmienia licencji modeli i materiałów innych gier.
Pochodzenie portów opisuje `data/selected-rosters.json` i `THIRD_PARTY.md`.

## Co naprawia

Wcześniejsza redukcja liczby ścian działała na osobnych wyspach rozciętych po
UV. Część drobnych powierzchni znikała zamiast tworzyć ciągłe ubranie. Naprawa
odczytuje wskazane oryginalne części portów MDL, prawidłowo rozcina powtarzane
współrzędne UV do istniejącego atlasu i przywraca ich pełne trójkąty. Nie stosuje
nowego DECIMATE, uproszczonego wypełniania dziur ani globalnego odwracania ścian.

| Postać | Przywrócone materiały |
| --- | --- |
| Geralt | `chain`, `torso`, `pants`, `boots`, `gloves` |
| Ciri | `dlccloth` |
| Yennefer | `cloth`, `glove`, `stocking` |
| Triss | `TRISS_CLOTH_COLOR` |
| Keira | `dress1`, `dress2` |
| Avallach | `clothes` |
| Zoltan | `clothes.001` |

Pozostałe części, w tym twarze i włosy, zachowują dokładne rozwinięte atrybuty
obecnej wersji. Tekstury i INI nie są zapisywane ani zmieniane. Prawdziwe
wycięcia alfa stroju Ciri pozostają takie jak w istniejącym atlasie.

U Avallacha wybierany jest oryginalny wariant opcjonalnego bodygroup `mask=null`.
Usuwa to wyłącznie 309 ścian akcesorium zasłaniającego twarz, zachowując pełne
3542 trójkąty autentycznej głowy oraz oczy i usta. Nie tworzy się nowej twarzy
ani nie zmienia tekstur; wybór zapisuje kontrakt przepisu.

Zachowane są aktualne 19-kościowe adaptery, pozycje pivotów, tracki animacji,
klatki i ich czasy, hierarchia oraz wszystkie węzły poza siatką skin. Oryginalne
pozycje kości MDL są dopasowywane do bind-pivotów odtworzonych z aktualnych
rekordów skina; nowe części nie dostają innego szkieletu lub animacji.

Wierzchołki łączone są wyłącznie przy identyczności pełnych 68 bajtów pozycji,
normalnej, UV i 36-bajtowego rekordu skina. Pozostają szwy UV i różne wagi.
Indeksy muszą mieścić się w 16 bitach; przekroczenie limitu kończy się błędem,
nie usunięciem ścian.

Jeżeli źródłowe palce, buty lub ubranie minimalnie wychodzą poza dotychczasowy
obrys po redukcji, jawna opcja rozszerza tylko render AABB do dokładnej sumy
starego obrysu i nowych ekstremów float32. Kontrakt zapisuje politykę osobno dla
każdej postaci: Ciri, Keira i Avallach zachowują zaakceptowany obrys przy zgodności
źródłowych ekstremów w tolerancji 0,002 jednostki; cztery pozostałe postacie
wymagają dokładnego poszerzenia. Nie obcina się wierzchołków, nie dodaje
marginesu do rozszerzanego obrysu ani nie skaluje modelu. Kolizje, fizyka i
zaczepy piłki nie zmieniają się. Raport podaje wartości i offsety pól.

## Lokalne zależności

- Blender 5.2.3 LTS z Pythonem/NumPy; przetestowano na Windows.
- Zewnętrzny SourceIO w wersji obsługującej MDL49, udostępniony lokalnie jako
  katalog pakietu z `__init__.py`. SourceIO nie jest vendoryzowany.
- Własne lokalne źródła portów MDL w katalogach o identyfikatorach Workshop
  zapisanych w `authoring/witcher-clothing-contract.json`.
- Dokładna instalacja lub payload moda beta2 jako aktualna baza rig-u,
  animacji i atlasów. Czysta bazowa gra nie zawiera wymaganych adapterów.

Każdy MDL, VVD i DX90 VTX ma przypięty hash. Przepis sprawdza także bazową
siatkę, atlas i INI; inna wersja danych kończy się błędem. Nie pobiera plików,
nie uruchamia Lua z portów, gry ani instalatora.

## Polecenia

Przykład dla Geralta, uruchamiany z głównego katalogu repozytorium. Ścieżki są
przykładami — żaden dysk ani katalog użytkownika nie jest zaszyty w narzędziach.

```powershell
blender --background --threads 2 --python authoring/read_witcher_clothing.py -- --character geralt --workshop-root 'D:/Zrodla/witcher-workshop' --profile-target 'C:/Gry/PetSoccerGMW-beta2' --sourceio 'D:/Narzedzia/SourceIO' --output 'build/clothing/geralt-input'
blender --background --threads 2 --python authoring/restore_witcher_clothing.py -- --character geralt --profile-target 'C:/Gry/PetSoccerGMW-beta2' --source-extract 'build/clothing/geralt-input' --output 'build/clothing/geralt-output' --allow-render-bounds-expansion
```

Nazwę postaci można zmienić na dowolną z tabeli. Pierwszy etap zapisuje prywatny
NPZ i raport źródłowy. Drugi tworzy osobny model w jego ścieżce `Data/` i raport.
Oba wyjścia muszą być nowe i rozłączne z wejściami; nic nie jest instalowane.
Pośrednie NPZ to dane modeli, nie kod źródłowy do publikacji.

Opcja `--dry-run` odczytuje i sprawdza dane bez zapisywania NPZ/modelu. Drugi
etap wymaga istniejącego wyniku pierwszego etapu również przy `--dry-run`.
Można uruchomić go zwykłym Pythonem z NumPy zamiast przez Blendera.

Wynik musi mieć dokładny hash i rozmiar z kontraktu wszystkich siedmiu postaci.
Różnice wersji parsera lub obliczeń zmiennoprzecinkowych kończą się błędem przed
zapisem; narzędzie nie akceptuje podobnego wizualnie, ale innego wariantu.
Kontrole działają także przy zoptymalizowanym uruchomieniu Pythona.

## Zakres sprawdzeń

Przenośny etap zapisu odtworzył w pamięci dokładne hashe wszystkich siedmiu
kandydatów. Osobny test przenośnego odczytu oryginalnego MDL Geralta potwierdził
identyczność siedmiu tablic wejściowych: pozycji, normalnych, UV, kości, wag,
etykiet materiałów i bind-pivotów. Testy nie zapisały modeli ani NPZ.

To sprawdzenie przepisu i danych. Ocena natywnego wyglądu obejmuje oddzielne
testy w grze; sam hash, liczba ścian czy render offline jej nie zastępują.
Przywrócone powierzchnie zwiększają liczbę trójkątów i pracę skina względem
uszkodzonego LOD. Pełne liczby zapisuje raport każdego modelu; nie jest to
deklaracja wzrostu FPS ani nowa redukcja tekstur.
