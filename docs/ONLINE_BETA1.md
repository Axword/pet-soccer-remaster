# 0.2.0-beta.1 — Online i Jagniellonia

Nowe wydanie rozszerza poprzednią betę o Online1vs1, ranking, wspólną pauzę,
Jagniellonię i kosmetyczne warianty oryginalnych zwierząt. Dodatkowe kluby są
domyślnie ukryte; włącza je opcja Audio video → Więcej opcji.

## Naprawione ustawienia

Stary parser skryptów menu traktuje zakończenia wierszy inaczej niż nowe
narzędzia tekstowe. Wcześniejszy generator zamienił CRLF na LF i menu opcji
ładowało się jako puste drzewo. Generator zachowuje teraz CRLF; kontrola
istnienia przycisków i fontów odrzuca niekompletny ekran. Pokazywanie, powrót,
widoczność rodzica i cykl zamykania mają osobną obsługę.

W silniku sprawdzono menu w oknach1024×768 i1920×1080, powrót przez Escape,
przyciski przez rzeczywisty callback silnika i trzy ponowne otwarcia.
Rzeczywisty selektor zmieniał się z12 na17 klubów, w tym gatunek58.
Nie oznaczamy tego jako testu fizycznego kliknięcia myszą.

## Jagniellonia

Siedem modeli: Slawomir Bramowicz, Bartek Welnowik, Taras Baranczuk,
Jesus Imaaaz, Afimico Puchulu, Tomasz Franekowski, Bernardo Welnital.
Podlaska Polana wykorzystuje styl i technikę bazowej mapy farmy.
Klub ma pięć strojów, herb i opis w oryginalnym układzie menu.

Oczy przylegają teraz do głowy; pojedyncze okrągłe źrenice nie korzystają
z rozciągniętego fragmentu atlasu. Sprawdzono geometrię, skinning, LOD-y,
pięć natywnych tekstur i podglądy front/bok/¾ wszystkich siedmiu modeli.
Finalnej poprawki oczu nie oglądano ponownie w silniku: użytkownik korzystał
z komputera i dalszy test pulpitu został wstrzymany. Nie deklarujemy pełnego
testu meczu nowego klubu ani wszystkich kombinacji strojów i map.

Nowych nazw Jagniellonii nie nagrano. Klub ma celowo wyciszone odziedziczone
nazwy, żeby nie odtwarzał poprzednich, niepasujących komentarzy.

## Online — rzeczywisty zakres testów

Serwer rozsyła stan hosta zamiast uruchamiać dwie niezależne symulacje.
Wcześniejszy test dwóch natywnych klientów na jednym komputerze obejmował
pełną minutę meczu i porównywanie stanu/zegara. Późniejszy test pauzy używał
jednego natywnego hosta i bezokienkowego klienta protokołu: oba żądania pauzy
(Escape hosta i żądanie gościa) zamroziły piłkę oraz zegar, trwały około15s
i zakończyły się automatycznym powrotem do gry. Test ukończył mecz remisem.

Są również testy protokołu, lobby, rankingu, rozłączeń, trwałości SQLite,
ograniczeń kolejek i odmowy błędnych danych. Nie testowano dwóch fizycznych
komputerów przez Internet. Publiczne konto, szyfrowanie i odporny na oszustwa
globalny ranking nie są częścią tego prototypu.

Paczka zawiera własny oficjalny CPython Windows embeddable wraz z licencją,
więc lokalny broker nie zależy od ścieżek Blendera lub instalacji autora.
Nie dołączamy prywatnej bazy rankingu ani logów. Baza powstaje przy pierwszym użyciu.

## Wygląd, wydajność i bezpieczeństwo publikacji

Polerowanie bazowych map zachowuje rozmiary, formatBC1 i pełne poziomy mipmap.
Nie zmienia kolizji, pozycji obiektów, granic boiska ani danych restartów.
Różnice zwierząt są kosmetyczne; ich fizyka pozostaje bazowa.
Nie publikujemy niepotwierdzonej liczby FPS ani gwarancji braku wszystkich crashy.

Łaty nowych aliasów czytają pliki źródłowe z oryginalnej instalacji,
a wynik zapisują w nowym folderze moda. Nie przesyłamy pełnych, niezmienionych
zasobów gry tylko dlatego, że w modzie otrzymały inne nazwy.

Otwieranie wielu natywnych kopii gry naraz nie jest zalecane. Pochodzenia
zgłoszonego zawieszenia całego komputera nie udało się jednoznacznie ustalić.
Zwykły launcher chroni przed drugim uruchomieniem tej samej instalacji.

[Sumy plików i wyniki końcowej instalacji](verification/online-beta1.json):
6305 odtworzonych plików zgodnych z manifestami,3826 oryginalnych plików
bez zmian oraz próba serwera Online z faktycznie zainstalowanego runtime.
Test instalatora nie uruchamiał okna gry.
