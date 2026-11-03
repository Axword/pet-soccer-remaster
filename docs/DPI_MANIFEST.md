# Manifest DPI pliku startowego

Publiczna paczka odtwarza `PetSoccer.bum` przez małą deltę, zamiast dołączać
pełny program gry. Wspierane wejście ma SHA256
`967fe819c058da9dfe6e062c9def44a0354437e7db7a5e2df0c23cffee7cae66`;
wynik ma SHA256 `5c3ece35611df9a17f81bb69d635534cc100753f7b2929ef73a94f5bb2d456cf`.

Sekcje wykonywalne `.text`, `.rdata` i `.data` są identyczne. Różnica dotyczy
nagłówków i zasobów PE: osadzonego manifestu `PetSoccer.CrossoverRemaster`
z `dpiAware=true`. Zapobiega dodatkowej wirtualizacji współrzędnych przez Windows.
Nie jest to modyfikacja logiki silnika ani mechanizmu ładowania JNI.

Własny XML jest również dostępny w paczce jako `PetSoccer.bum.manifest`
i `PetSoccer.exe.manifest`. Przy eksperymencie na **nowej lokalnej kopii** można
użyć Windows SDK Manifest Tool (`mt.exe`), np.:

```powershell
mt.exe -manifest 'PetSoccer.bum.manifest' '-outputresource:C:/Gry/kopia/PetSoccer.bum;#1'
```

Różne wersje narzędzia mogą ułożyć zasoby i nagłówki inaczej, więc to przykład
odtworzenia deklaracji DPI, nie obietnica identycznego hashu PE. Dokładne bajty
wydania odtwarza zweryfikowana delta z `package/patches.tsv`. Instalator nigdy
nie zapisuje do oryginalnego pliku; tworzy wynik w osobnej kopii moda.
