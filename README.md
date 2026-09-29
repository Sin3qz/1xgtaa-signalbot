# 1xGTAA (defensiv, ungehebelt)

Discord- + ntfy-Signalbot (GitHub Actions) fuer die **1xGTAA (defensiv, ungehebelt)**-Strategie.
Gleiche, bewaehrte Infrastruktur wie der 3xSpyTips-Bot (`letsgo-signalbot`) — alle
Bugfixes B1–B12/F1–F4 uebernommen. Der Strategie-Kern ist unabhaengig gegen den
verifizierten v6-Backtest geprueft (0 Abweichung auf 5517 Handelstagen).

## Strategie
7 Bausteine, Top-2 nach Momentum, **40/60-Tilt** (Platz-2-UEbergewicht). Trend **SMA8 > SMA150**, Momentum = Summe 1/3/6/9-M. Verifiziert: CAGR 16,0 / Sortino 1,25 / MaxDD −18,2.

- **Signale:** ausschliesslich auf zuverlaessigen **USD-1x-Kursen** (Yahoo), Entscheidung
  von gestern wirkt heute (`.shift(1)`, kein Look-Ahead). Momentum-Fenster = 21/42/63/126/189 Handelstage.
- **Rebalancing:** Cooldown-Modell — **taegliche** Entscheidung, 10-Handelstage-Freeze.
- **ntfy (Handy-Push):** nur bei tatsächlichem Handel. Täglich läuft eine Discord-Statusmeldung.


## Änderungen 29.09.2026 (Strategie-Parameter unverändert)
- ntfy nur bei tatsächlichem Handel, jetzt über den Vergleich mit der zuletzt gemeldeten Allokation
  (`notify_state_1xgtaa.json`): keine doppelten Meldungen an Wochenenden/Feiertagen oder bei Retries, kein verpasster
  Wechsel bei verspäteten Daten; ntfy nur mit frischen Daten.
- Schmale, handytaugliche Tabellen (Discord-Codeblock, ntfy ohne Codeblock).
- Datenprüfung vor jeder Berechnung (letzter Kurs, Lücken, Sprünge > 30 %).
- Dashboard-Zeitbalken zeigt Platz 1 (gehaltenes Asset mit höchstem Momentum).
- `strategies/gtaa_botcore.py` und alle Parameter sind unverändert; neu `strategies/common.py`.
- **ntfy nur an echten Handelstagen (NYSE):** Wird ein Wechsel am Wochenende/Feiertag erkannt (Signal Freitagsschluss),
  kommt die Push-Meldung am nächsten Handelstag morgens („heute handeln“). Discord zeigt vorher „⏳ Wechsel erkannt —
  handeln am …“. Fehlen am Handelstag frische Daten, holt der nächste Handelstag die Meldung nach („verspätet“).
  Der ntfy-Zustand wird erst nach erfolgreichem Push gespeichert.
- **Cooldown-Zähler korrigiert:** Rechengitter = NYSE-Handelstage (wie der Backtest-Datensatz). Die alte Version nahm den
  QQQ-Index als Gitter; fehlte bei Yahoo ein Tag dauerhaft, fiel er heraus und der 10-Tage-Cooldown lief einen Tag zu
  lang. Jetzt zählt jeder Handelstag (fehlender Kurs = letzter Kurs fortgeschrieben). Fehlt bei einem US-Titel der
  jüngste Tag, endet das Gitter am letzten gemeinsamen Tag → keine Entscheidung auf alten Kursen, Retry läuft.
- **Frische-Prüfung auf den echten Kursdaten** (nicht auf fortgeschriebenen Werten); EMU Value (Xetra) darf wegen
  Xetra-Feiertagen bis 4 Kalendertage alt sein.
- Hinweis Backtest-Datensatz: Im alten v6-Datensatz hat die EMU-Value-Reihe seit 08/2022 an Xetra-Feiertagen Lücken
  (NaN); dadurch war EMU Value dort nach jedem Feiertag 150 Tage lang ausgeschlossen (Ø-Anteil 2023–26: 2 % statt 27 %).
  Der Bot schreibt den letzten Xetra-Kurs fort (so wie alle anderen Bots) — das ist die korrekte Umsetzung der Regel.

## Signal-Ticker
`QQQ` Nasdaq100 · `EEMS` EM-SmallCap · `AW1T.DE`×`EURUSD=X` EMU-Value (USD-Alt.: `FEZ`) · `IEF` Treasury7-10y · `GLD` Gold · `DBC` Rohstoffe · `BIL` Cash

## Dateien
```
main.py                      # Einstieg (Vertrag: run_strategy -> (signal, ntfy_text, discord_text))
send_ntfy.py                 # ntfy-Push, wirft nie (F1/B10)
strategies/constants.py      # ALLE Parameter (Single Source of Truth, B4/B11)
strategies/gtaa_botcore.py   # verifizierter Strategie-Kern (unverändert)
strategies/common.py         # Kalender, Download, Datenprüfung
strategies/runner.py         # Download + Frische + History + Nachricht + status_*.json
.github/workflows/notify.yaml
history_1xgtaa.txt            # Allokations-Historie (committet, fuer Dashboard)
status_1xgtaa.json            # aktueller Stand (committet, fuer Dashboard)
```

## Setup (Kurz — Details im GTAA_Signalbots_Setup.md)
1. Repo **public** anlegen, Dateien am **exakten Pfad** ablegen (v.a. `.github/workflows/notify.yaml`, B12).
2. Secrets: `DISCORD_WEBHOOK_URL`, `NTFY_TOPIC` (langer, geheimer Name; optional `NTFY_SERVER`).
3. **Settings → Actions → General → Workflow permissions → „Read and write permissions"** (B8!).
4. Actions-Tab → „Run workflow" testen. Cron: `17 5 * * *` (07:17 Berlin).

KEINE ANLAGEBERATUNG.

## Ausfallsicherheit und Datenprüfung (Stand 29.09.2026)
- **Vor jeder Berechnung** je Kursreihe: Datum des letzten Kurses (US: zuletzt erwartete NYSE-Sitzung; Sensex/Xetra/FX:
  max. 4 Kalendertage alt), fehlende Handelstage, Sprünge > 30 %, Mindestlänge der Historie und Vergleich des
  Historienbeginns mit dem letzten Lauf (abgeschnittene Yahoo-Antwort), bei Indizes Schluss = Vortag (Platzhalter).
- **Keine Entscheidung und keine ntfy**, wenn eine Prüfung fehlschlägt (veraltet, abgeschnitten, unplausibler Sprung am
  jüngsten Tag, Kalender nicht ladbar): `needsRetry` → 2 Wiederholungen im Abstand von 30 Min, zusätzlich
  **Sicherheitslauf 11:47 UTC** (läuft nur, wenn der Morgenlauf nicht erfolgreich war). Fehlt bei einem US-Signal der
  jüngste Tag, rechnet der Bot nur bis zum letzten gemeinsamen Tag (keine fortgeschriebenen Kurse als Entscheidungsbasis).
- **Download fehlgeschlagen**: kein Handel, keine ntfy; letzter gültiger Stand bleibt im Dashboard (Handelsanweisung wird
  entfernt), Discord meldet den Fehler. Der nächste erfolgreiche Lauf rechnet alles aus der vollen Historie neu (auch den
  Cooldown) und holt eine fällige ntfy-Meldung am nächsten Handelstag nach („verspätet“).
- **Workflow-Fehler** (Installation/Start): Discord bekommt eine Fehlermeldung; Discord- und Commit-Schritt laufen immer
  (`if: always()`), Push mit 3 Versuchen — der ntfy-Zustand geht nicht verloren (keine Doppelmeldung).
- **Erststart/verlorener Zustand**: Ist ein Wechsel noch nicht gehandelt, wird er trotzdem gemeldet.
- Ist dauerhaft kein `NTFY_TOPIC` gesetzt, gilt die Meldung als erledigt (nur Discord), statt täglich „verspätet“ zu wiederholen.
