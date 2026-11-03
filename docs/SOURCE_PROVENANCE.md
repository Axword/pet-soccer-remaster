# Źródła wydania Online beta1

Zakres autorskiego kodu obejmuje `src/java`, `src/native`, `src/patches`,
narzędzia budowania oraz receptury `authoring`. Licencja MIT nie obejmuje
oryginalnej gry ani postaci, tekstur, dźwięków i modeli innych wydawców;
ich status opisuje [THIRD_PARTY.md](../THIRD_PARTY.md).

Pełne źródła własnego launchera, brokera i testów konsolowych są w
`src/online`; odtwarzanie ich z czystego checkoutu opisuje
[ONLINE_BUILD.md](ONLINE_BUILD.md). Binariów oficjalnego CPython nie powiela
się w tym katalogu źródłowym.

Nie dołączono zdekompilowanych implementacji oryginalnych klas, pełnych
`code.pak`, silnika gry, JRE, prywatnych profili ani bazy rankingu.
Przepisy bajtkodu zapisują tylko autorskie zmiany i odciski metod; oryginalne
bajty muszą być dostarczone lokalnie z obsługiwanej instalacji.

| Źródła | Pochodzenie i rola |
| --- | --- |
| `CXOnlineTransport`, `CXOnlineMenu`, `CXOnlineLobbyModel` | Własny transport Java1.3 i UI pokoi/rankingu; model Online5 z bramką widoczności klubów. |
| `CXOnlineMatch`, `CXOnlineState`, `CXOnlinePause` | Własna synchronizacja gospodarza/gościa, zegar, wynik, wspólna przerwa i wznowienie. |
| `CXOnlineVisibility`, `CXOptions` | Zarządzanie własnymi panelami i przywracanie wcześniejszych kontrolek, kursora oraz fokusu. |
| `CXAnimalIdentity` | Dobór kosmetycznych wariantów; fizyczne wymiary pozostają z modelu bazowego. |
| `CXJagniellonia` | Definicje klubu58, mapy42, siedmiu nazw, barw i wariantów modeli. |
| `CXTeamVisibility` | Selekcja12 oryginalnych lub17 wszystkich klubów, bez modyfikowania zapisów i odblokowań. |
| `CXSpecialBall`, `special_ball.py` | Strażnik niepoprawnego stanu strzału specjalnego z zaakceptowanego etapu przed LoL. |
| `CXLoLProfile`, `lol_profile.py` | Przywrócenie jednego klubu LoL, siedmiu postaci i mapy39. |
| `CXHumanPreview`, `CXGMWProfile` | Aktualny etap GMWL056: podglądy i zamknięty zestaw GMW+LoL; późniejsze hooki Jagniellonii nakłada przepis. |
| `src/native` | Własny mostek JNI, aktualne źródła options004, pozostałe własne moduły renderowania, wejścia i strażników fizyki. |
| `online_ui.py`, `online_match.py`, `animal_identity.py`, `jagniellonia.py`, `team_visibility.py` | Fingerprintowane dodatki do klas dostarczanych lokalnie; nie zawierają ich pełnych implementacji. |
| `tools/build_online*.py`, `prepare_online_options.py` | Izolowane odtwarzanie archiwum i menu; jawne wejścia, nowe wyjścia, CRLF. |
| `authoring/features` | Oryginalne algorytmy kosmetycznych wariantów, łagodnego retuszu12 map, Jagniellonii i poprawki siedmiu par oczu. |

## Sprawdzenie odpowiadania źródeł

Przebudowano etap Online z lokalnego wejścia GMWL
`6fbcaedbdba9dacbda3e5921c4af16d8a928f3e9109108a71f0916ff17924cd4`.
Każdy z **453 wpisów** archiwum i ich kolejność odpowiadał bajt w bajt
normalnej wersji016, której pełny ZIP ma SHA256
`b119c4f5d3181bcf1e8ad8f8c52306bc874ba8345db0178fe585d8c0c38859c4`.
Nie obejmuje to ewentualnych późniejszych, jawnie opisanych zmian launchera
lub brokera, które nie wchodzą do tego archiwum Java.

Nowy ZIP źródłowego sprawdzianu ma SHA256
`ede05d64531f75a975a356199c48de08d78dc6387d1596c9d209cc742b42756d`:
różnią się wyłącznie metadane ZIP nowych wpisów. Indeks jest identyczny:
`8cbb6bfe2e2ddf48a109b26dbcc869f8b5c8ad63c62d55212f448ab1e7a1f380`.
Nie jest wymagana identyczna data kompresji archiwum do zachowania bajtów klas.

Oddzielnie skompilowano wszystkie22 własne pliki Java do32 klas major47.
Weryfikator rzeczywistego JVM z `-Xint -verify` zaakceptował42 zmienione
lub nowe klasy, bez inicjalizacji silnika. Istniejące testy źródeł i
historycznego przepisu podglądów zakończyły się wynikiem15 PASS, bez pominięć.
Mostek C++ buduje się jako PE32 x86 z zewnętrznymi nagłówkami JNI;
38 nazw eksportów i cała sekcja wykonywalna `.text` są identyczne z
zaakceptowanym mostkiem004. Różne metadane linkera nie stanowią gwarancji
identycznego hashu całego DLL.
Dziewięć skryptów Online/Main/Pause i `CXOptions.scr` odtworzono dokładnie;
wszystkie zachowują CRLF. Odcisk `CXOptions.scr`:
`7069010023ad10df0f7593542136a27702c6c50a42a4ab8b58e3b60354708696`.

Nowe narzędzia authoring przeszły27 sprawdzeń, w tym pełne odtworzenie7
modeli Jagniellonii zgodnych z zatwierdzonymi SHA256. Różnice numeryczne
w historycznie wyliczanych normalnych stabilizuje mała tabela własnych,
zaakceptowanych normalnych. Nie zawiera ona geometrii, UV, animacji ani
wag skórowania. Wejście każdego wariantu ma kontrolowany hash; poprawka
oczu działa dopiero po wszystkich zmianach sylwetki. Dokładny zakres i
ograniczenia opisuje [authoring/features](../authoring/features/README.md).

To dowody kompilacji i zgodności danych, nie deklaracja pełnego testu gry.
Rzeczywisty zakres testów silnika i ograniczenia prototypu podaje
[ONLINE.md](ONLINE.md). Prywatne sterowniki testowe, ich archiwa oraz klasy
`QA`, `Probe`, `Stub` i `Fixture` nie są częścią gry ani publikowanych źródeł.
