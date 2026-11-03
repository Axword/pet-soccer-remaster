# Pet Soccer Remaster + Fun Clubs — Online beta

Fanowski mod Pet Soccer z poprawkami obrazu, obsługą dwóch padów, turniejem,
nową **Jagniellonią Białystok** i prototypem **Online 1vs1** z lobby oraz rankingiem.
Zachowuje styl i 12 zwierzęcych drużyn oryginału.

**Wersja 0.2.0-beta.1. To beta — zgłaszaj błędy w [Issues](https://github.com/Axword/pet-soccer-remaster/issues).**

[**⬇ Instalator Windows — Online beta**](https://github.com/Axword/pet-soccer-remaster/releases/download/v0.2.0-beta.1/PetSoccer-Remaster-Online-Setup.exe)

[Pliki moda ZIP](https://github.com/Axword/pet-soccer-remaster/releases/download/v0.2.0-beta.1/PetSoccer-Remaster-Online-ModFiles.zip)
· [Wydanie i sumy kontrolne](https://github.com/Axword/pet-soccer-remaster/releases/tag/v0.2.0-beta.1)
· [Strona projektu](https://axword.pl/mods)
· [Wesprzyj autora](https://buycoffee.to/axword)

## Instalacja

1. Potrzebujesz oryginalnej polskiej wersji Pet Soccer. Gra nie jest dołączona.
2. Uruchom instalator i wskaż folder oryginalnej gry.
3. Wybierz **nowy folder**. Instalator utworzy osobną kopię; oryginału i jego zapisów nie zmienia.
4. Uruchom nowy skrót lub `PetSoccer-Online.exe` z folderu moda.

Python do Online jest dołączony. Nie trzeba instalować Blendera, Pythona ani pip.
Pierwszy start: 1024×768 w oknie, czysty profil **Gracz** z odblokowanymi
oryginalnymi drużynami, boiskami i poziomami trudności. Nie jest to prywatny zapis autora.

## Gdzie są dodatkowe kluby?

Domyślnie widoczne jest 12 oryginalnych klubów.
**Audio video → Więcej opcji → Dodatkowe kluby: WŁ.** udostępnia:

- **Jagniellonię Białystok** — siedmiu jagnięcych zawodników, pięć strojów,
  herb i boisko **Podlaska Polana**.
- **Borussię Blockmund** — Minecraft.
- **Górnika Khorinis** — Gothic.
- **Wiedźminhampton** — Wiedźmin.
- **Real Runeterra** — League of Legends.

Nie ma wybieralnych drużyn polityków, dziennikarzy ani polskiego esportu.

## Online

Przycisk **Online** otwiera połączenie z serwerem, listę pokojów i ranking.
Jeden gracz tworzy pokój, drugi dołącza; obaj wybierają drużyny i gotowość.
Host prowadzi wspólny stan meczu: piłkę, zawodników, wynik i zegar.
**Escape daje obu graczom 15 sekund przerwy, po czym mecz wznawia się automatycznie.**

To prototyp do **LAN lub własnego serwera**. Nie ma publicznego, stale
utrzymywanego serwera ani kont. Domyślne `127.0.0.1` jest połączeniem lokalnym,
nie wyszukiwaniem innych komputerów. Ranking W/R/P i win rate są zapisane na
konkretnym serwerze. [Łączenie dwóch komputerów i uruchamianie serwera](docs/ONLINE.md).

## Pozostałe zmiany

- Naprawione puste „Więcej opcji”, powrót do ustawień i przełączanie dodatkowych klubów.
- Poprawione oczy wszystkich siedmiu modeli Jagniellonii.
- Oryginalne zwierzęta różnią się delikatnie proporcjami i ubarwieniem,
  przy zachowaniu wymiarów fizyki i zasad gry.
- Delikatne wyostrzenie istniejących 12 map, bez zwiększania pamięci ich tekstur.
- Obsługa padów, oddzielny tryb okna/pełnego ekranu i wyższe rozdzielczości,
  przełączany remaster, oryginalne czcionki oraz panele zawodników.
- Poprawki podglądów Gothica, Wiedźmina i LoL-a, restartów gry i obsługi niepoprawnych pozycji piłki.
- Lokalny **Multiplayer → TURNIEJ**: osiem drużyn i drabinka; mecz od jednej minuty
  (2×30 s), a przy remisie w turnieju złoty gol.

[Zakres sprawdzeń i ograniczenia tej wersji](docs/ONLINE_BETA1.md).

## Źródła

| Ścieżka | Zawartość |
| --- | --- |
| `src/native`, `src/java` | Autorskie części mostka JNI, menu, Online, animacji i pozostałych poprawek. |
| `src/patches`, `tools` | Jawne, sprawdzające wejścia przepisy zmian i narzędzia budowania. |
| `src/online` | Serwer, launcher i testy Online. |
| `authoring` | Przepisy tworzenia modeli, tekstur i map. |
| `installer`, `delta.py` | Instalator i mechanizm łat, także aliasów zasobów oryginału. |
| `package`, `metadata` | Pliki moda, łaty i manifest obsługiwanej oryginalnej instalacji. |
| `tests`, `docs` | Testy, instrukcje, pochodzenie źródeł i granice weryfikacji. |

Kod autorski jest na licencji **MIT**. Materiały gier i runtime Pythona mają
odrębne licencje: [THIRD_PARTY.md](THIRD_PARTY.md). Repozytorium nie zawiera
kompletnej oryginalnej gry, silnika ani JRE. Zmienione zasoby oryginału, także
kopie pod nowymi nazwami, instalator odtwarza z lokalnych plików i łat.

[Budowanie](docs/BUILDING.md) · [Pochodzenie nowych źródeł](docs/SOURCE_PROVENANCE.md)

Przy zgłoszeniu błędu podaj wersję, drużyny, mapę, tryb gry, rozdzielczość i kroki
odtworzenia. Logi przejrzyj pod kątem prywatnych danych. Nie przesyłaj całej gry.
