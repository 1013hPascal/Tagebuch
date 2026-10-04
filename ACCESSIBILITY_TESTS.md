# Barrierefreiheit: Teststrategie

Wie im Chatbot-Projekt gibt es zwei Ebenen:

1. **Automatisiert** (pytest-qt, `python -m pytest`): simulierte Tastendrücke und Klicks
   prüfen Tab-Reihenfolge, Accessible Names, Menüaufbau, Ansagen-Inhalte, Fokus nach
   Ansichtswechseln. 154 Tests, siehe `tests/`. Läuft ohne echten Screenreader und ohne
   Bildschirm (`QT_QPA_PLATFORM=offscreen`).
2. **Manuell mit echtem NVDA** (diese Datei): Tastatur- und Screenreader-Verhalten lässt
   sich nur teilweise simulieren - insbesondere Kontextmenü-Tasten und tatsächliche
   Sprachausgabe müssen von einer Person mit laufendem NVDA geprüft werden.

Zum Debuggen: Jede Ansage wird zusätzlich nach `%APPDATA%\Tagebuch\logs\app.log` geloggt
(Zeile `Ansage: ...`) - falls NVDA etwas nicht vorliest, lässt sich dort prüfen, ob die
Ansage überhaupt ausgelöst wurde.

## Manuelle Checkliste

Spalte „Ergebnis“ zum Ausfüllen beim Testen (OK / Problem + Beschreibung).

### Einrichtung und Anmeldung

| # | Prüfpunkt | Ergebnis |
|---|---|---|
| 1 | Beim allerersten Start erscheint der Einrichtungsdialog, Fokus liegt im Feld „Passwort“ | |
| 2 | NVDA liest beim Tabben die Beschriftungen „Passwort“ und „Passwort wiederholen“ vor, nicht nur „Bearbeitbarer Text“ | |
| 3 | Unterschiedliche Passwörter: Fehlermeldung wird vorgelesen, Felder sind danach leer, Fokus zurück im ersten Feld | |
| 4 | Escape im Einrichtungsdialog schließt die Anwendung (kein Account angelegt) | |
| 5 | Beim zweiten Start erscheint der Anmeldedialog mit Feld „Passwort“ | |
| 6 | Falsches Passwort: Fehlermeldung wird vorgelesen, Feld ist leer, Fokus im Feld | |

### Hauptfenster und Menüs

| # | Prüfpunkt | Ergebnis |
|---|---|---|
| 7 | Nach der Anmeldung landet der Fokus auf dem obersten Listeneintrag „Was ich zu erzählen habe“ | |
| 8 | Alt öffnet die Menüleiste, NVDA liest „Datei“ vor (nicht nur den Programmnamen) | |
| 9 | Im Menü Datei wird der erste Eintrag „Suche/Frage“ beim Öffnen automatisch vorgelesen | |
| 10 | Menü Rückschau: Strg+1/2/3 wechseln die Ansicht, der aktive Eintrag ist als ausgewählt markiert (NVDA sagt „markiert“ o. ä.) | |
| 11 | Nach jedem Rückschau-Wechsel liegt der Fokus auf dem ersten Listeneintrag | |

### Übersicht (Tag/Monat/Jahr)

| # | Prüfpunkt | Ergebnis |
|---|---|---|
| 12 | Pfeiltasten in der Liste lesen jeden Eintrag vor, inkl. „(heute)“ beim heutigen Tag | |
| 13 | Tab von der Liste springt in die Vorschau (NVDA liest „Vorschau“ als Namen), Umschalt+Tab zurück | |
| 14 | Vorschau beim obersten Eintrag liest den Hinweistext vor (z. B. „Neuen Eintrag für heute schreiben.“) | |
| 15 | Kontextmenü-Taste bzw. Umschalt+F10 auf einem echten Eintrag öffnet ein Menü mit „Eintrag löschen“ und „Zusammenfassung neu erstellen“; auf dem obersten Eintrag öffnet sich kein Menü | |
| 16 | Löschen fragt nach („wirklich löschen?“, Standard ist Nein), Fokus danach auf dem nächsten Eintrag | |
| 17 | Entf-Taste löscht ebenfalls (mit derselben Rückfrage) | |

### Editor (mit und ohne Spracheingabe)

| # | Prüfpunkt | Ergebnis |
|---|---|---|
| 18 | Editor für heute öffnet mit Fokus in „Was geschah“, Cursor am Ende des Textes | |
| 19 | Tab-Reihenfolge: Datum → Was geschah → Ich muss dir was erzählen → Speichern → zurück zu Datum | |
| 20 | In „Was geschah“ bewegt Tab den Fokus weiter (fügt kein Tabzeichen ein), Eingabetaste erzeugt einen Zeilenumbruch | |
| 21 | Klick auf „Ich muss dir was erzählen“: NVDA sagt „Aufnahme läuft“ an, Knopftext wechselt zu „Aufnahme beenden“ | |
| 22 | Erneuter Klick: „Wird umgewandelt …“ wird angesagt, Knopf ist kurz deaktiviert | |
| 23 | Nach der Umwandlung: „Text eingefügt“ wird angesagt, Fokus bleibt auf dem Knopf, Text steht unten im Feld | |
| 24 | Editor zum Bearbeiten eines vergangenen Eintrags: kein Spracheingabe-Knopf, Tab-Reihenfolge Datum → Was geschah → Speichern, Cursor beim Öffnen am Anfang | |
| 25 | Ungültiges Datum: konkrete Fehlermeldung, Fokus geht ins Datumsfeld | |
| 26 | Speichern: „Gespeichert“ wird angesagt, zurück zur Übersicht mit Fokus auf dem gespeicherten Eintrag | |
| 27 | Escape mit ungespeicherten Änderungen fragt „Änderungen speichern?“ mit Ja/Nein/Abbrechen | |

### Leseansicht

| # | Prüfpunkt | Ergebnis |
|---|---|---|
| 28 | Öffnen eines vergangenen Tages/Monats/Jahres: Fokus in der Textausgabe am Anfang, NVDA liest den Accessible Name (z. B. „Eintrag vom 21.09.2026“) beim Fokussieren vor | |
| 29 | Tab zum Knopf „Bearbeiten“, Enter oder Klick öffnet den Editor; bei einem Tageseintrag mit Spracheingabe (Cursor am Ende), bei Monat/Jahr ohne (Cursor am Anfang) | |
| 30 | Escape geht zurück zur Übersicht, Fokus auf dem zuvor gewählten Eintrag | |

### Suche/Frage

| # | Prüfpunkt | Ergebnis |
|---|---|---|
| 31 | Strg+F öffnet den Dialog „Suche/Frage“, Fokus im Feld „Suchbegriff oder Frage“ | |
| 32 | Ergebnisliste: oberste Zeile „Suchergebnisse für „X“: N Treffer“ wird vorgelesen, ist aber nicht aktivierbar | |
| 33 | Monats-/Jahrestreffer werden mit Kennzeichnung vorgelesen (z. B. „Monatsübersicht September 2026“) | |
| 34 | Vorschau eines Treffers enthält zusätzlich den Textausschnitt um die Fundstelle | |
| 35 | Enter auf einem Treffer öffnet ihn wie in der Übersicht; Escape geht zurück zur zuletzt aktiven Übersicht | |
| 36 | Eingabe mit „?“ (z. B. „Wann war ich zuletzt im Urlaub?“): nach dem Suchen erscheint zusätzlich das Feld „KI-Antwort“ mit Ansage „Antwort wird gesucht …“, danach die Antwort mit Ansage „Antwort gefunden.“ und Fokus im Antwortfeld | |
| 37 | Ohne laufendes Ollama erscheint im selben Feld eine verständliche Fehlermeldung statt einer Antwort | |

### Passwort ändern und Account löschen

| # | Prüfpunkt | Ergebnis |
|---|---|---|
| 36 | Passwort ändern: falsches altes Passwort wird klar gemeldet, Fokus bleibt im Dialog | |
| 37 | Account löschen: Warnhinweis wird beim Öffnen vorgelesen, Standardknopf ist „Abbrechen“ | |
| 38 | Account löschen mit richtigem Passwort: zurück zum Einrichtungsdialog, keine Anwendung wird beendet | |

### Allgemein

| # | Prüfpunkt | Ergebnis |
|---|---|---|
| 39 | Alle Dialoge lassen sich mit Escape schließen | |
| 40 | Hintergrundmeldungen (Statuszeile, Zusammenfassungen) unterbrechen nie das Tippen und verschieben nie den Fokus | |
| 41 | Keine Information wird nur über Farbe vermittelt (Hochkontrastmodus testen) | |
