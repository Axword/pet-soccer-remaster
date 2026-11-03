# Online — prototyp 1 na 1

Budowanie własnego launchera/serwera i testy bez silnika gry:
[ONLINE_BUILD.md](ONLINE_BUILD.md).

Wydanie `v0.2.0-beta.1` dodaje przycisk **Online**, pokoje, gotowość obu
graczy i ranking wybranego serwera. Jest to własny prototyp sieciowy moda.
Nie wymaga Blendera ani ręcznej instalacji Pythona w gotowym instalatorze.

## Uruchomienie i połączenie

Uruchom skrót **Pet Soccer Remaster Online** (`PetSoccer-Online.exe`),
a następnie wybierz **Online** w menu gry. Launcher pilnuje jednej instancji
tej kopii gry i przygotowuje lokalny serwer pomocniczy. Dla gry lokalnej
domyślny adres to `127.0.0.1`, port `27888`.

Aby grać na dwóch komputerach w sieci lokalnej:

1. Na komputerze gospodarza uruchom `Uruchom-Serwer-LAN.cmd`. Ten serwer
   używa portu `27889`, oddzielnie od pomocniczego serwera launchera.
2. W **Online → Ustawienia** obie osoby wpisują adres IP tego komputera
   w sieci lokalnej oraz port `27889`. Gospodarz może użyć `127.0.0.1:27889`.
3. Ustawcie różne pseudonimy, wybierzcie **Połącz**. Jedna osoba tworzy pokój,
   druga do niego dołącza. Po wybraniu klubów obie osoby wybierają **Gotowy**.

Połączenia przez Internet wymagają samodzielnie dostępnego serwera,
przekierowania odpowiedniego portu albo prywatnej sieci VPN. Wydanie nie
zapewnia centralnie hostowanej listy wszystkich pokoi. Instalator nie zmienia
zapory sieciowej ani ustawień routera. Gra i serwer obu osób muszą pochodzić
z tego samego wydania; sesje używają wersji `GMWL-6fbcaedb-online5`.

Jeżeli port27888 zajmuje poprzednie lobby, do połączenia z innym serwerem
możesz użyć `Online - polacz ze swoim serwerem.cmd` (launcher `--remote`).
Lokalny serwer pozostaje uruchomiony po zamknięciu gry. Przed aktualizacją
lub odinstalowaniem zamknij mecz i uruchom **Zatrzymaj-Lobby.cmd** z tej
instalacji — zatrzymuje tylko jej własny serwer, bez zamykania innych Pythonów.

## Pauza, zegar i wyniki

Gospodarz rozstrzyga stan meczu, piłkę, zegar i wynik; druga instancja odbiera
migawki oraz wysyła sterowanie. To nie jest niezależna symulacja obu komputerów.
**Escape** podczas Online włącza wspólną **15-sekundową przerwę**. Zegar i
sterowanie obu osób zostają zatrzymane. Serwer automatycznie kończy przerwę;
kolejne naciśnięcia nie wydłużają trwającej przerwy. Escape nie wraca wtedy do menu.

Ranking pokazuje wygrane, remisy, porażki oraz procent zwycięstw liczony jako
`wygrane / (wygrane + remisy + porażki)`. Liczą się zakończone mecze ze zgodnymi
raportami wyniku obu uczestników. Zerwane lub porzucone sesje nie dopisują
zwycięstwa. Dane przechowuje wybrany serwer, a nie globalne konto gracza.

Prototyp używa pseudonimów bez uwierzytelniania i nie zapewnia ochrony przed
podszywaniem się lub oszustwami gospodarza. Używaj go ze znanymi graczami.
W paczce nie ma wcześniejszej bazy rankingu ani prywatnych wyników autora.

## Dodatkowe kluby i Jagniellonia

Domyślnie widoczne jest 12 oryginalnych klubów. Aby włączyć dodatki, wybierz
**Opcje → Audio video → Więcej opcji → Dodatkowe kluby: WŁ.**. Ustawienie
dotyczy wyboru drużyn lokalnego i Online; nie usuwa zapisów ani definicji klubów.
Każda osoba w Online powinna włączyć dodatki, jeżeli chce ich używać.

Do wyboru dochodzą:

- **Jagniellonia Białystok** — jagniaki, Podlaska Polana, żółto-czerwone stroje.
- **Borussia Blockmund** — Minecraft.
- **Górnik Khorinis** — Gothic.
- **Wiedźminhampton** — Wiedźmin.
- **Real Runeterra** — League of Legends.

Jagniellonia ma siedmiu zawodników: Sławomir Bramowicz, Bartek Wełnowik,
Taras Barańczuk, Jesus Imaaaz, Afimico Puchulu, Tomasz Franekowski i
Bernardo Wełnital. W plikach gry pisownia części nazw pozostaje ASCII dla
zgodności ze starymi fontami. Nowe nazwy Jagniellonii i LoL nie mają nagranego
dubbingu; celowo nie zastępują ich losowe nazwy oryginalnych zawodników.

## Zakres sprawdzeń

Przed wydaniem wykonano testy transportu, listy pokoi, wyników, limitów kolejek,
rozłączeń i pauzy. W izolowanym teście dwóch instancji na jednym komputerze
porównano stan i zegar meczu. Osobny test silnika potwierdził zamrożenie czasu
podczas przerwy i automatyczne wznowienie po około 15 sekundach.

Menu **Więcej opcji** sprawdzono w silniku przy 1024×768 oraz 1920×1080
w oknie: widoczne kontrolki i fonty, Escape, powrót oraz kilka ponownych wejść.
Przełączenie dodatków zmienia rzeczywistą listę z 12 na 17 klubów i zawiera ID58.
Publiczne źródła przebudowano osobno, bez uruchamiania kolejnego renderera.
Nie oznacza to pełnego testu Internetu na dwóch komputerach, wszystkich map,
wszystkich rozdzielczości ani gwarancji braku awarii starego silnika.

## Odtwarzanie źródeł Online

Pełne archiwa gry nie są źródłami tego repozytorium. Poniższy etap wymaga
lokalnie odtworzonego GMWL sprzed Online, z `code.pak` o SHA256
`6fbcaedbdba9dacbda3e5921c4af16d8a928f3e9109108a71f0916ff17924cd4`.
Wcześniejsze przepisy beta3, `special_ball.py` i `lol_profile.py` pozostają
w repozytorium; każdy ma własny sprawdzany etap wejściowy. Nie usuwaj ich
asercji, aby wymusić działanie na nieznanej wersji gry.

```powershell
python tools/build_online.py --game 'C:/Gry/Pet Soccer' --baseline 'C:/Gry/GMWL-etap' --ecj 'tools/external/ecj-3.7.2.jar' --output build/online
python tools/build_online_scr.py --game 'C:/Gry/GMWL-etap' --output build/online-scr
python tools/prepare_online_options.py --input 'C:/Gry/GMWL-etap/Data/Menu/scr/CXOptions.scr' --output build/online-options/Data/Menu/scr/CXOptions.scr
python tools/build_native.py --jni-dir 'C:/narzedzia/jni' --output build/native-online
```

`build_online.py` kompiluje tylko 11 potrzebnych rodzin własnych klas, dodaje
hooki w sprawdzanej kolejności i zastępuje istniejącą własną `CXOptions`.
Pozostałe klasy oryginalnej gry zachowuje w lokalnym wyniku. Całe wynikowe
archiwum pozostaje poza Git i trafia do paczki wyłącznie przez mechanizm delt.
Nie zastępuj wszystkich klas wynikiem ogólnego `compile_java.py`: część
własnych klas starszych etapów ma następnie dodatkowe hooki.

Java pozostaje zgodna z 1.3, major47. `-Xint -warn:none` omija problemy
formattera starego środowiska podczas kompilacji ECJ. Mostek musi być PE32 x86.
Opcje wymagają **razem** aktualnej `CXOptions.java`, aktualnego `modern.cpp`
i skryptu `CXOptions.scr` z zakończeniami **CRLF**. Samo powodzenie parsera
nie potwierdza, że załadował kontrolki.

Wszystkie te narzędzia piszą do nowego katalogu, nie do działającej instalacji.
Receptury assetów i wymagana kolejność poprawki oczu są opisane w
[authoring/features](../authoring/features/README.md).
