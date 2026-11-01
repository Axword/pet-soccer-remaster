# Beta 2: multiplayer, stroje i modele

Poprawiono dwie niezależne przyczyny błędów:

- Parser menu multiplayera nie przyjmował liczb `.95` i `.025`. Wszystkie trzy
  warianty rozdzielczości używają teraz `0.95` i `0.025`.
- Po zmianie oryginalnego klubu na dodatkowy lista barw zachowywała pięć starych
  przycisków, mimo krótszej tablicy tekstur. Kliknięcie takiej pozycji mogło
  przerwać podgląd albo uruchomienie meczu.

`CXTeamColours` odbudowuje listę, wyznacza faktyczną liczbę strojów i sprawdza
indeks przy odczycie tekstur, zapisie wyboru, podglądzie oraz tworzeniu zawodnika.
Trzy dodatkowe kluby mają po jednym istniejącym stroju, z własną ikoną klubu.
Nie dodano pozornych alternatywnych barw. Oryginalne kluby zachowują pięć strojów.

Naprawiono też przejścia turnieju: funkcja chowania menu obejmuje wszystkie 20
zarejestrowanych ekranów, w tym dodatkowy setup i drabinkę. Setup wyłącza swój
podgląd postaci. Drabinka ma trzy kolumny 8→4→2, większe obszary nazw obok logo,
oryginalną złotą ramkę oraz czcionki faktycznie ładowane w danej rozdzielczości.
Pary są losowane raz przy rozpoczęciu nowego turnieju. Powrót z meczu, rysowanie
ekranu i podwójne kliknięcie nie przelosowują aktywnej drabinki.

Wariant wydania udostępnia 12 oryginalnych klubów oraz:

| Świat | Klub | Skrót |
| --- | --- | --- |
| Minecraft | Borussia Blockmund | BBM |
| Gothic | Górnik Khorinis | GKH |
| Wiedźmin | Wiedźminhampton | WHP |

Nie udostępnia drużyn polityków, dziennikarzy ani polskiego esportu. Istniejące
zaakceptowane nagrania nadal używają krótkich nazw światów; nowych nazw klubów
nie nagrywano.

## Zmniejszenie kosztu animacji

Siedem modeli Wiedźmina i szkielet Minecrafta miały powielone identyczne dane
wierzchołków. Bezstratne scalenie zmniejsza liczbę skinnowanych wierzchołków
Wiedźmina o 72–78%, szkieletu o 60,5%, a pliki łącznie o 16 841 424 bajty.
Trójkąty, pozycje, normalne, UV, materiały, pełne dane kości/wag, animacje,
pivoty i obrysy pozostają takie same. Piksele tekstur pozostają bez zmian.
Nie jest to pomiar wzrostu FPS ani gwarancja czasu ładowania na innym komputerze.

## Odtworzenie poprawek

Pracuj wyłącznie na nowej lokalnej kopii. Najpierw skompiluj własne klasy zgodnie
z BUILDING.md. Przepisy bajtkodu sprawdzają odciski znanych metod wejściowych:

```powershell
python tools/apply_recipe.py club_names --input build/beta1-code.pak --output build/named-code.pak
python -m src.patches.wardrobe --game 'C:\Gry\PetSoccerGMW-beta1' --code-input build/named-code.pak --helper build/java/CXTeamColours.class --output build/wardrobe
python tools/apply_recipe.py tournament --input build/wardrobe/code.pak --compiled build/java --output build/tournament-code.pak
python tools/build_bracket_layout.py --game 'C:\Gry\Pet Soccer' --output build/tournament-ui
python tools/compact_skinned_mesh.py --input 'C:\Gry\PetSoccerGMW-beta1\Data\Meshes\Animals' --output build/compact --pattern 'cx_w3_*.3da'
python tools/verify_compacted_mesh.py --source 'C:\Gry\PetSoccerGMW-beta1\Data\Meshes\Animals' --output build/compact
```

Folder wardrobe zawiera także zaktualizowany indeks klas i trzy pliki menu;
sama podmiana code.pak nie wystarcza. Generator turnieju odtwarza sześć plików
SCR na podstawie lokalnych zasobów oryginalnej polskiej gry. Dla szkieletu uruchom kompakcję osobno
z `--pattern cx_mc_skeleton.3da`. Narzędzia nie nadpisują plików wejściowych.

## Faktycznie wykonane sprawdzenia

- Oryginalna Java 1.3: weryfikacja klas i 684 asercje dotyczące strojów/indeksów.
- Weryfikacja 15 klubów i zachowania bazowych 12 drużyn.
- Turniej: 43 asercje rzeczywistych metod chowania ekranów i 22 575 asercji
  reguł; 128 drabinek i 896 spotkań wykonanych w teście logiki, z jawnymi atrapami
  granic interfejsu. Nie są to mecze rozegrane w silniku.
- Jawne źródła odtwarzają wszystkie 429 wpisów archiwum (427 klas) i sześć nowych plików turnieju.
- Dwa niezależne odczyty 21 modeli: bitowo identyczne rozwinięte narożniki
  trójkątów, dane skórowania i animacje; osiem plików zmienionych.
- Działająca gra: logowanie i wejście do menu multiplayera przy 1024×768 w oknie.

Weryfikacja JVM nie zastępuje renderowania. Końcowy test wizualny nowej drabinki
i przejścia „Graj” został przerwany przed wczytaniem poprawki. Pełna macierz
meczów, urządzeń, rozdzielczości i pomiarów płynności pozostaje poza tym
sprawdzeniem; wydanie pozostaje betą.
