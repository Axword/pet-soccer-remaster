# Beta3 — podglądy postaci i poprawki grafiki

Wersja `0.1.0-beta.3` poprawia podglądy Gothica i Wiedźmina oraz powierzchnie
ubrań. W rzeczywistym silniku obejrzano fronty wszystkich 14 postaci przy
1024×768 w oknie; niezależny recenzent zatwierdził pokazane ujęcia.

## Zmiany

- Podglądy 7 postaci Gothica i 7 Wiedźmina używają właściwych animacji
  bezczynności/rozglądania. Poprawiono kierunek postaci, czyszczenie poprzedniej
  animacji, szybkie przełączanie, ponowne wczytanie oraz pozycje Cup/Instant.
- Naprawiono ubrania siedmiu postaci Wiedźmina. Wcześniejszy DECIMATE na
  rozdzielonych wyspach UV usuwał powierzchnie rękawów, tułowia i nóg.
  Przywrócono wskazane autentyczne części źródłowe, zachowując atlas, UV,
  istniejący rig i ścieżki animacji. Avallach ma wariant z odsłoniętą twarzą.
- Usunięto techniczne opisy z podglądów trzech klubów. Nazwy to
  **Borussia Blockmund**, **Górnik Khorinis** i **Wiedźminhampton**.
  Dwa ekrany menu używają odpowiedników nazw zgodnych ze starym fontem;
  kanoniczne dane drużyn pozostają bez zmiany.
- Delikatnie poprawiono zapisane normalne skał i roślin na dodatkowych boiskach
  Old Camp i Kaer Morhen. Geometria, tekstury i kolizje tych map są zachowane.

Naprawa zachowuje materiały i flagi renderowania gry.

## Koszt i zakres modeli

Suma wierzchołków siedmiu skinów wzrosła z **81 003 do 164 228**, a pliki
siatek łącznie o **7 530 946 B**, czyli około **7,53 MB**. To koszt przywrócenia
utraconych powierzchni; bezstratne scalanie pełnych atrybutów pozostało aktywne.
Nie wykonano pomiaru FPS.

Największe rozszerzenie zapisanego AABB wynosi **0,182072 jednostki** i dotyczy
wyłącznie obrysu renderowania. Nie zmienia fizyki, kolizji ani zasad meczu.
Nie wypełniano zamierzonych wycięć alfa, kart włosów czy otworów ubrań.

## Co sprawdzono

| Kontrola | Potwierdzony zakres |
| --- | --- |
| 15 publicznych testów Python | Przepisy, zakres zmian i zabezpieczenia wejść. |
| 1164 prywatne asercje JVM | Rzeczywiste poprawione klasy; jawne atrapy granic natywnego silnika. To nie test GPU. |
| Dwa przepisy Java | Referencyjne odtworzenie dokładnych bajtów finalnego archiwum i indeksu. |
| Siedem siatek Wiedźmina | Zgodność źródłowych narożników, rigów/tracków i hashy wejść; osobny audyt obrysów. |
| Dwie poprawki map | Dokładny zakres normalnych i porównania renderów offline. Bez deklaracji testu meczu na tych boiskach. |
| Natywny silnik | Fronty wszystkich 14 modeli, przełączanie siedmioosobowych drużyn, próbki podglądów Cup44 i Instant51. Geralt ma ciągłe buty/rękawice na jasnym tle, Avallach czytelną twarz bez opcjonalnej maski. |
| Paczka i instalator | 356 plików moda i 19 łat odtworzonych niezależnie; instalacja i odinstalowanie zakończone poprawnie. 4182 pliki zgodne z listą, 3826 plików źródłowej gry bez zmian; zmieniony zapis i dodany plik użytkownika zachowane przy odinstalowaniu. |

Referencyjny `code.pak` ma **431 wpisów ZIP: 429 klas i 2 wpisy metadanych**.
SHA256:
`82cf7b366d8c54d5f99368ad4c34301bf077f26666c277f94f8753bf17a051f5`.

Indeks `code_inf.pak`:
`ef5d1c392976f6a5f0bd31bf2239c69e5ef798dfc26a072164f4dc87e512ef04`.

## Odtwarzanie i granica publikacji

Kolejność dwóch przepisów i wymagane lokalne wejścia opisuje
[BUILDING.md](BUILDING.md). Szczegóły:
[podglądy](HUMAN_PREVIEW.md), [normalne map](MAP_NORMAL_POLISH.md) oraz
[odtwarzanie ubrań Wiedźmina](WITCHER_CLOTHING_REPAIR.md).

Oryginalna gra i źródłowe MDL/VVD/VTX pozostają lokalne. Pośrednie NPZ,
prywatne sterowniki QA, zmodyfikowane klasy testowe silnika, kompletne PAK-i
i całe kopie gry nie są materiałem do publikacji w repozytorium.

Pokazane ujęcia nie potwierdzają każdego kąta kamery, wszystkich kombinacji
trybów, rozdzielczości ani płynności pełnego meczu. Mapy oceniono w renderach
offline. Wydanie pozostaje betą.

[Sumy kontrolne i wyniki weryfikacji paczki](verification/beta3-package.json).
