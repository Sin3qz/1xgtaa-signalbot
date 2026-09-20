# 1xGTAA (defensiv, ungehebelt)

Discord- + ntfy-Signalbot (GitHub Actions) fuer die **1xGTAA (defensiv, ungehebelt)**-Strategie.
Gleiche, bewaehrte Infrastruktur wie der 3xSpyTips-Bot (`letsgo-signalbot`) — alle
Bugfixes B1–B12/F1–F4 uebernommen. Der Strategie-Kern ist unabhaengig gegen den
verifizierten v6-Backtest geprueft (0 Abweichung auf 5517 Handelstagen).

## Strategie
7 Bausteine, Top-2 nach Momentum, **40/60-Tilt** (Platz-2-UEbergewicht). Trend **SMA8 > SMA150**, Momentum = Summe 1/3/6/9-M. Verifiziert: CAGR 16,0 / Sortino 1,22 / MaxDD −22,0.

- **Signale:** ausschliesslich auf zuverlaessigen **USD-1x-Kursen** (Yahoo), Entscheidung
  von gestern wirkt heute (`.shift(1)`, kein Look-Ahead). Momentum-Fenster = 21/42/63/126/189 Handelstage.
- **Rebalancing:** Cooldown-Modell — **taegliche** Entscheidung, 10-Handelstage-Freeze.
- **ntfy (Handy-Push):** NUR bei echtem Handelswechsel (taeglich moeglich, wie beim 3xSpyTips-Bot). Taeglich laeuft eine
  Discord-Statusmeldung.

## Signal-Ticker
`QQQ` Nasdaq100 · `EEMS` EM-SmallCap · `AW1T.DE`×`EURUSD=X` EMU-Value (USD-Alt.: `FEZ`) · `IEF` Treasury7-10y · `GLD` Gold · `DBC` Rohstoffe · `BIL` Cash

## Dateien
```
main.py                      # Einstieg (Vertrag: run_strategy -> (signal, None, text))
send_ntfy.py                 # ntfy-Push, wirft nie (F1/B10)
strategies/constants.py      # ALLE Parameter (Single Source of Truth, B4/B11)
strategies/gtaa_botcore.py   # verifizierter Strategie-Kern (identisch in allen 3 Bots)
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
