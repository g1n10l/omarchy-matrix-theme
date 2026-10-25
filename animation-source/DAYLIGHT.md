# Oświetlenie za oknem co 30 minut

Obie włączone obudowy mają osobne pomarańczowe kontrolki pracy dysków obok
zielonych kontrolek zasilania. `disk_activity.py` nadaje im różne rytmy mignięć
czytelne także przy 2 klatkach na sekundę. To animacja aktywności, nie pomiar
operacji dyskowych. Kontrolki są nakładane po oświetleniu pokoju, więc zachowują
pomarańczową barwę w każdym przedziale dnia, nocy i podczas migotania lampy.
Korzysta z nich także generator bazowej animacji.

Kontroler wylicza oświetlenie osobno dla każdego półgodzinnego przedziału.
Nie przełącza już tapety między czterema kategoriami dzień, świt, zachód i noc.
Na podstawie daty, strefy czasowej i współrzędnych w `../daylight.json` oblicza
wysokość słońca, jasność, gammę, nasycenie i ciepłą barwę światła.
Zmiany są próbkowane o pełnej godzinie i 30 minut po niej.

Filtry zmieniają światło w oknie i przy lampie. W ciągu dnia wygaszają źródło
światła lampy oraz redukują jego ciepłe odbicia na sprzęcie, przewodach i blacie.
Osobna maska odbić zachowuje szczegóły przedmiotów zamiast zaczerniać cały obszar.
Główny CRT pokazuje 30-minutową symulację opisaną poniżej. Boczny CRT pokazuje
pomiary systemowe w stylu htop. Migotanie lampy nadal działa, gdy słońce
jest poniżej -6 stopni. Zmiana oświetlenia i migotanie korzystają ze wspólnej
blokady, żeby nie podmieniać tapety jednocześnie.

Maska wyłączonej żarówki obejmuje całe wnętrze i obrzeże klosza oraz wystającą
żarówkę. Jej przejście leży poza otworem lampy, dzięki czemu nie przecina
żarówki ani nie zostawia jasnego łuku na obrzeżu. Dzienny filtr skaluje
jasność i usuwa ciepłą barwę, zachowując kształt oraz szczegóły żarówki, zamiast
odejmować jasność do czerni. Osobno tłumi poświatę pod kloszem i ciepłe odbicia
na blacie i sprzęcie. Korekta odbić również skaluje kolory, bez zaczerniania
cieni. Siła obu efektów rośnie płynnie o świcie i maleje o zmierzchu.

Film dla danego przedziału powstaje przy pierwszym użyciu i jest przechowywany
w `../daylight/half-hour/RRRR-MM-DD/HHMM+OFFSET-lamp-off-v2.mp4`. Offset odróżnia powtórzone
przedziały przy jesiennej zmianie czasu. Generowanie filmu o długości 30 minut
może potrwać kilka minut; dotychczasowy film gra do czasu zakończenia renderowania. Starsze pliki
czterech wariantów pozostawiono dla zgodności z istniejącymi odnośnikami, ale
nowy kontroler ich nie wybiera.

## Symulacja na głównym CRT

Każdy nowy wariant oświetlenia ma film długości dokładnie 1800 sekund.
Główny ekran pokazuje kolejno dziesięć etapów po trzy minuty: rozpoznanie,
skanowanie portów, enumerację, identyfikację usług, audyt, analizę, próby
w piaskownicy, śledzenie tras, weryfikację i raport. Tekst zmienia się co
sekundę. To lokalnie wygenerowana animacja, bez wykonywania poleceń i ruchu
sieciowego. Po 30 minutach wraca do początku. Końcowe wiersze przechodzą
w początkowy widok terminala.

Wspólny generator `hacking_terminal.py` jest używany w każdym przedziale
półgodzinnym i wariancie migotania lampy. Parametry oraz treść terminala są
częścią klucza pamięci podręcznej, więc starszy film z pętlą 12 sekund nie
zostanie wybrany. Nie trzeba z góry generować wariantów dla całego roku.

Ekrany są składane z osobnych strumieni z własnymi znacznikami czasu:
główny CRT ma cykl 1800 sekund, a mały CRT powtarza zapis 12 sekund pomiarów
systemu. Powrót małego CRT do początku nie przewija ani nie resetuje
głównej symulacji. Generator tworzy mały ekran osobno od oświetlenia pokoju
i głównego terminala. Test filmu
porównuje oba ekrany w sekundach 0 i 12: mały wraca do tego samego widoku,
a główny ma już inną treść. Zmiana całego filmu przez odtwarzacz nadal
uruchamia oba strumienie od początku.

## Monitor systemu na małym CRT

`system_monitor.py` pobiera rzeczywiste liczniki `/proc/stat`, `/proc/meminfo`,
`/proc/loadavg`, `/proc/uptime` oraz statystyki procesów `/proc/PID/stat`.
Pokazuje użycie CPU, pamięć RAM i swap, load average, uptime, liczbę procesów
oraz pięć procesów posortowanych według użycia CPU i pamięci. Procent CPU
wynika z przyrostów liczników pomiędzy pomiarami, a nie z losowej animacji.
Nagłówek pokazuje godzinę pomiaru w Europe/Warsaw.

To kompaktowy widok w stylu htop, bez zależności od programu htop, który nie
jest zainstalowany. Na każdy nowy przedział oświetlenia powstają 24 pomiary
co pół sekundy. Ich 12-sekundowy film jest powtarzany przez resztę przedziału.
Nie jest to aktualizowany na żywo monitor procesów. Rzeczywiste dane pobiera
usługa pulpitu podczas generowania wariantu; film zostaje przełączony po renderze.

`../daylight/system-monitor/latest.json` zawiera czas, źródłowe pomiary i identyfikator
przestrzeni PID, a `latest.mp4` zawiera nagranie. Kopia z izolowanego środowiska
agenta jest oznaczana jako SANDBOX. Usługa pulpitu nie używa jej jako danych
całego systemu, ponieważ pamięć podręczna sprawdza także przestrzeń PID.
Zachowywany jest tylko ostatni zestaw pomiarów. Test obliczeń:
`python test-system-monitor.py`.

Krótkie filmy pokoju z oświetleniem powstają w `../daylight/room-loops` i są
usuwane po udanym renderowaniu. Generator nakłada na nie długą animację CRT.
Wynik ma 2 klatki na sekundę,
co pozwala pokazać przewijanie i migający kursor bez renderowania 43200 klatek
dla każdego przedziału. Test sekwencji: `python test-hacking.py`.

## Zastosowanie

W terminalu sesji graficznej uruchom:

```sh
~/.config/omarchy/themes/matrix/animation-source/apply-animation.sh
```

Skrypt przeładuje jednostki użytkownika, uruchomi odtwarzacz i timer oraz
zastosuje bieżący półgodzinny przedział. Timer `matrix-daylight.timer` używa
`OnCalendar=*-*-* *:00,30:00`.

Podgląd parametrów bez zmiany pulpitu:

```sh
python daylight.py --status
python daylight.py --at 2026-12-21T17:30
```

Wygenerowanie filmu bez przełączania tapety:

```sh
python build-daylight.py
python build-daylight.py --at 2026-12-21T17:30
```

## Odtwarzanie i testy

Kontroler wznawia animację i sprawdza, czy czas odtwarzania postępuje. Niedostępny,
uszkodzony lub zatrzymany renderer jest restartowany. Zapis filmu odbywa się
przez plik tymczasowy, pełną kontrolę dekodowania i atomową podmianę, więc błąd
renderowania nie niszczy dotychczasowego nagrania.

`~/.config/systemd/user/owed.service.d/matrix-rendering.conf` ustawia
`OWE_HWDEC=no` i `LIBGL_ALWAYS_SOFTWARE=true`, aby ominąć błędy sterownika
widoczne w logach. Ustawienie dotyczy odtwarzacza tapet wszystkich motywów i może
zwiększyć zużycie CPU. Usunięcie tego pliku i restart usługi po `daemon-reload`
przywraca domyślny sposób renderowania.

```sh
python test-playback.py
python verify-animation.py
```

`verification.json` zawiera kontrolę filtrów wszystkich półgodzin bieżącej daty,
kontrolę ruchu obu CRT w aktualnym nagraniu i parametry 48 przedziałów dla każdej
z czterech sezonowych dat. Przy zmianie czasu dzień może zawierać 46 lub 50
przedziałów. Kontrola plików nie zastępuje sprawdzenia pulpitu na żywo.

## Pora roku i Europe/Warsaw

Obliczenia i timer są jawnie przypięte do `Europe/Warsaw`, niezależnie od
zmiennej `TZ` i strefy systemowej. CET/CEST i obie zmiany czasu wynikają z bazy
IANA. Daty `--at` z offsetem są przeliczane do Warszawy z zachowaniem tej samej
chwili; nieistniejąca lokalna godzina podczas wiosennej zmiany czasu jest
odrzucana. Dla powtórzonej godziny jesiennej można podać `+02:00` albo `+01:00`.

Przybliżona geometria słoneczna jest oparta na równaniach NOAA:
https://gml.noaa.gov/grad/solcalc/solareqns.PDF
Rok przestępny i część doby są uwzględnione. Parametry orbity są wyliczane
w UTC, dzięki czemu ta sama chwila daje ten sam wynik niezależnie od sposobu
zapisu czasu. Wysokość słońca steruje jasnością, gammą i barwą okna.
To umowna symulacja wyglądu światła, nie pomiar luksów. Część słoneczna nie modeluje orientacji okna ani przesłaniania go przez
sąsiednie budynki. Korektę meteorologiczną opisano poniżej.

`test-solar.py` obejmuje CET/CEST, obie zmiany czasu, daty z offsetem, wysokość
słońca podczas przesileń i równonocy oraz wszystkie półgodziny roku 2024 i 2026.
`solar-verification.json` zawiera sezonowe wyniki dla Krakowa. Przykładowo
model daje około 16,4 godziny dnia w czerwcu i 8,1 godziny w grudniu.

Nazwy plików wynikowych zawierają teraz także skrót parametrów renderowania
i źródła. Po zmianie obliczeń nie zostanie użyty film ze starej pamięci
podręcznej tylko dlatego, że data i godzina są takie same.

## Pogoda dla Krakowa

`weather_light.py` pobiera `cloud_cover`, `precipitation` i `weather_code`
z publicznego API Open-Meteo dla współrzędnych z `daylight.json`.
Źródło danych i opis parametrów: https://open-meteo.com/en/docs
Dane są wynikiem modeli meteorologicznych, nie odczytem czujnika za oknem.
Open-Meteo udostępnia je z atrybucją CC BY 4.0.

Zachmurzenie i opady osłabiają światło i nasycenie barw, a kod mgły WMO 45/48
obniża kontrast widoku za oknem. Kody śniegu osłabiają kontrast. Nie są dodawane
sztuczne krople deszczu ani płatki śniegu. Ekrany CRT i wyłączanie lampy za dnia
zachowują dotychczasowe działanie. Pozycja słońca i Europe/Warsaw nadal sterują
podstawowym oświetleniem. Korekta mgły jest wygaszana nocą, by nie tworzyć
sztucznie jasnego okna.

Zapytanie jest wykonywane najwyżej raz na półgodzinny przedział. Wynik jest
zapisywany atomowo w `~/.cache/matrix-weather.json`. Po błędzie sieci ponowna
próba następuje po pięciu minutach. Ostatni wynik pozostaje dopuszczalny przez
maksymalnie 6 godzin od czasu danych; starszy lub błędny wynik zostaje pominięty
na rzecz samego modelu słonecznego. Skrypt nie wymaga klucza API.

`daylight.py --status` pokazuje sekcję `weather` ze źródłem `Open-Meteo`, `cache`,
`stale-cache` lub `solar-only`. `--at` nie łączy się z siecią i nie nakłada
obecnej pogody na datę historyczną lub przyszłą. Drobne wahania zachmurzenia
są zaokrąglane, aby nie renderować ponownie filmu przy każdej niewielkiej zmianie.

Testy obsługi danych i trybu offline: `python test-weather.py`.

## Usuwanie filmów z poprzednich dni

Po udanej aktualizacji tapety kontroler usuwa wygenerowane filmy z katalogów
`daylight/half-hour/RRRR-MM-DD`, których data jest wcześniejsza niż dzisiejsza
w strefie Europe/Warsaw. Czyści także wcześniejsze zaległości. Działa podczas
normalnej pracy motywu Matrix, bez osobnego timera.

Zachowuje dzisiejsze i przyszłe nagrania, aktualnie wyświetlaną tapetę oraz
przygotowany film bieżącej aktualizacji. Nie usuwa plików źródłowych, kopii
zapasowych, dowiązań symbolicznych ani plików o nierozpoznanej nazwie. Puste
katalogi dat po sprzątaniu są usuwane. Usunięcia i odzyskane bajty trafiają do
logu usługi. Stary film aktywny o północy zostaje zachowany do kolejnej udanej
aktualizacji.

Ręczne uruchomienie samego sprzątania:

```sh
python ~/.config/omarchy/themes/matrix/animation-source/video_cleanup.py
```

Testy usuwania i ochrony plików: `python test-cleanup.py`.

## Korekta dziennej ekspozycji

Poprzednie połączenie niskiej gammy bazowej i silnego przyciemnienia chmur
nadmiernie zaciemniało już ciemne źródło. Dzienna gamma bazowa rośnie teraz
z pierwiastkiem udziału światła słonecznego, a korekta zachmurzenia jest łagodniejsza.
Dla sprawdzonego przedziału 25.10.2026 10:30 Europe/Warsaw przy zachmurzeniu
69% średnia jasność wycinka okna wynosiła około 53/255 przed korektą i 101/255
po niej. W źródle było to około 99/255. To wartości pikseli z tego samego
wycinka obrazu, a nie pomiar fizycznego natężenia światła za rzeczywistym oknem.
