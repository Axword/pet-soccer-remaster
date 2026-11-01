# Architektura

Pet Soccer korzysta z własnego silnika, biblioteki `ChromeEngine.dll` i klas
Java1.3 ładowanych z `code.pak`. Oryginalny program i środowisko uruchomieniowe
pozostają zewnętrznym wymaganiem.

## Mostek

`src/native/cxsupport.cpp` jest główną jednostką kompilacji 32-bitowej biblioteki
JNI `cxsupport.dll`. Dołącza bieżące źródła obrazu, HUD-u, komentarzy, padów,
map i zabezpieczeń fizyki. `src/java/CXSupport.java` deklaruje jego punkty JNI.
Pliki pod `ext` są autorskimi fragmentami, które podczas rozwoju znajdowały się
w innych katalogach. Zmieniono ich względne ścieżki dołączeń, nie logikę.

Sterowanie używa istniejących klas akcji gry. Dwa porty pada są przypisywane do
odrębnych kontrolerów drużyn; warstwa menu obsługuje też kursor i przyciski.
Przy pierwszym uruchomieniu świeżego profilu wykrywanie nie jest blokowane przez
ustawienia autora paczki.

## Klasy i przepisy zmian

Nowe klasy są dostępne jako zwykłe źródła Java. Modyfikacje klas istniejącej gry
opisują funkcje `apply` w `src/patches`; operują na bajtach przekazanych jawnie
przez wywołującego. Import tych modułów nie otwiera ani nie nadpisuje gry.

Historyczne etapy mają różne oczekiwane wejścia i odciski metod. Są przepisami
do audytu/rozwoju, a nie generatorem, który można bezwarunkowo uruchomić od nowa
nad dowolną wersją gry. Obecny instalator odtwarza dokładnie zweryfikowany stan
wydania z lokalnej, obsługiwanej wersji bazowej i łat.

## Turniej

`CXKnockout` przechowuje stan ośmiu uczestników i siedmiu spotkań w pamięci
sesji. Wynik musi odpowiadać konkretnemu oczekującemu obiektowi meczu i mieć
znacznik faktycznego zakończenia. Anulowanie lub ponowne pokazanie tabeli nie
przyznaje kolejnego zwycięstwa. Profil GMW deleguje wyłącznie początkowy dobór
drużyn do `CXGMWProfile`.

Reguła złotego gola rozszerza istniejący warunek gry; punktacja, powtórki,
zamiana stron i zakończenie po golu korzystają z oryginalnego przepływu.

## Profil GMW

Zachowane są historyczne indeksy tablic. Widocznych jest12 oryginalnych drużyn
oraz reprezentanci37/44/51: Minecraft/Gothic/Wiedźmin. Wyłączone dodatkowe
indeksy bezpiecznie wskazują oryginalnego robota, dzięki czemu brak innych
assetów nie wymusza przebudowy silnika. Dodatkowe dozwolone mapy mają indeksy
41/38/40. Szczegóły konfiguracji są w `data` i `src/java/CXGMWProfile.java`.

## Publiczny instalator

Manifest wskazuje wyłącznie potrzebne pliki bazowe. Zmiany istniejących plików
są odtwarzane z kopii użytkownika przez sprawdzane sumami SHA256 łatki;
niezmienione pliki nie są dystrybuowane. Nowe zasoby moda są jawne w paczce.
Instalacja odbywa się w nowym folderze poprzez katalog tymczasowy. Odinstalowanie
usuwa tylko pliki zgodne z zapisanym manifestem i zachowuje zmieniony zapis
oraz nowe pliki użytkownika.

