# Pet Soccer Remaster + Fun Clubs — beta

Fanowski mod Pet Soccer: poprawki obrazu i sterowania, obsługa dwóch padów,
dodatkowe drużyny **Gothic, Minecraft i Wiedźmin** oraz lokalny turniej z drabinką.
Oryginalne 12 drużyn pozostaje dostępne.

**To jest beta. Część funkcji może jeszcze działać niepoprawnie.**
Problemy, crashe i uwagi zgłaszaj w
[GitHub Issues](https://github.com/Axword/pet-soccer-remaster/issues).

[Pobierz wersję beta](https://github.com/Axword/pet-soccer-remaster/releases/tag/v0.1.0-beta.1)
· [Strona projektu](https://axword.pl/mods)
· [Wesprzyj autora](https://buycoffee.to/axword)

## Instalacja

1. Zainstaluj oryginalną polską wersję Pet Soccer. Gra nie jest dołączona do moda.
2. Pobierz instalator z zakładki Releases i wskaż folder oryginalnej gry.
3. Wybierz nowy folder docelowy. Instalator utworzy osobną kopię z modem;
   oryginalny folder i jego zapis pozostaną bez zmian.
4. Uruchom `PetSoccer.exe` z nowej kopii albo utworzony skrót.

Paczka zawiera czysty profil **Gracz** z odblokowanymi drużynami, boiskami i
poziomami trudności. Nie zawiera prywatnego zapisu ani postępu kariery autora.
Pierwszy start używa 1024×768 w oknie. Ustawienia Audio video udostępniają
wyższe rozdzielczości i oddzielny wybór okna/pełnego ekranu.

## Co zawiera

- Przełączany remaster, zachowane oryginalne czcionki i elementy menu.
- Obsługę padów w grze, wykrywanie urządzeń i rozdzielenie dwóch graczy.
- Panele z aktualnie kontrolowanymi zawodnikami.
- Trzy dodatkowe drużyny, po siedem różnych postaci, oraz ich mapy.
- Nazwy drużyn/zawodników i komentarze z głosami Gothic.
- Multiplayer → **TURNIEJ**: osiem drużyn, ćwierćfinały, półfinały i finał.
- Opcję jednej minuty meczu: dwie połowy po 30 sekund. Remis w turnieju
  uruchamia oryginalną regułę złotego gola.
- Poprawki restartów, ochrony przed niepoprawnymi pozycjami piłki i zbędnych
  operacji wykonywanych podczas meczu.

Drabinka działa w bieżącej sesji gry. Dotychczasowy tryb ligowy pozostaje osobno.

## Źródła i pliki

| Ścieżka | Zawartość |
| --- | --- |
| `src/native` | Pełny bieżący kod mostka JNI, obrazu, HUD-u, padów, komentarzy i zabezpieczeń fizyki. |
| `src/java` | Autorskie klasy interfejsu, drabinki i profilu GMW oraz deklaracje JNI. |
| `src/patches` | Jawne przepisy zmian bajtkodu: czas meczu, drabinka, wybór drużyn, logowanie, fizyka i optymalizacja. |
| `tools` | Edytor plików klas, kompilacja i tworzenie nowych, izolowanych PAK-ów. |
| `authoring` | Rzeczywiste przepisy eksportu modeli, animacji i map; uruchamiane w osobnym lokalnym workspace. |
| `installer` | Otwarty kod instalatora i mechanizmu kopiowania/łatek. |
| `package` / `metadata` | Pliki i manifesty paczki; niezmienione pliki gry kopiowane są z lokalnej instalacji. |
| `tests` | Testy reguł i narzędzi, generowanie czystego zapisu oraz testy bezpieczeństwa instalacji. |
| `docs` | Architektura, budowanie, zakres weryfikacji i pochodzenie źródeł. |

Kod autorskich części jest na licencji **MIT**. Modele, dźwięki, grafiki,
czcionki i dane łat z materiałów gier mają odrębny status — zobacz
[THIRD_PARTY.md](THIRD_PARTY.md). Repozytorium nie zawiera silnika, JRE,
kompletnej oryginalnej gry ani jej niezmienionych klas jako osobnych plików.

Instrukcja dla osób modyfikujących kod: [BUILDING.md](docs/BUILDING.md).

## Zgłaszanie problemów

Podaj wersję moda, Windows, rozdzielczość i tryb ekranu, liczbę padów, drużyny,
mapę oraz kroki prowadzące do błędu. Dla crasha dołącz odpowiedni fragment
logu po usunięciu prywatnych danych. Zrzut lub krótkie nagranie pomaga przy
błędach animacji i interfejsu. Nie przesyłaj całej gry.

## Stan weryfikacji

Sprawdzono kod, klasy Java w środowisku gry, reguły drabinki, zależności paczki
oraz instalację i odinstalowanie w osobnym folderze. Te sprawdzenia nie zastępują
pełnego testu wizualnego i dłuższych meczów na każdej konfiguracji. Płynność,
urządzenia wejściowe i nietypowe sytuacje meczowe mogą wymagać dalszych poprawek.

