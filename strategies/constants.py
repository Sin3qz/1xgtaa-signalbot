# ============================================================================
#  1xGTAA — defensiv, ungehebelt (7 Bausteine).  Cooldown-Modell (taegliche
#  Entscheidung, 10-Handelstage-Freeze), Top-2 nach Momentum, 40/60-Tilt (P2-UEG).
#  Cash-Fallback per Slot (Dual-Momentum): 40/0 o. 0/60, sonst Cash (strikt).
#  Ab 01.12.2026: Trend SMA15 > SMA160 (Momentum unveraendert 1/3/6/12, Cooldown 10; bis 30.11.2026:
#  SMA8/150; Stichtag in CFG['prev'], damit die Umstellung keine Umschichtung mitten im Monat ausloest).
#  Begruendung (Dashboard-Repo studien/STUDIE.md, Nachtrag 28.11.2026): zwei Datenbasen. (1) Echte Bot-Assets
#  09/2012-11/2026 (EMU Value vor 08/2022 mit MSCI EMU verkettet): 1/3/6/12 in 94 % der Paare vor 1/3/6/9 (Sharpe
#  1,12 vs. 0,97) -> Momentum 1/3/6/12; Minimax-Regret ueber drei Teilzeitraeume am kleinsten bei kurz 12-16 x lang
#  150-190. (2) Ersatzindizes 1995-2026 (MSCI EMU/EM statt EMU Value/EM Small Caps): Plateau kurz 13-27 x lang 130-180.
#  Schnittmenge kurz 13-16 x lang 150-170 -> Mitte SMA15 / SMA160. Cooldown: Plateau 8-12 -> 10.
#  Kein Look-Ahead.
#  Verifiziert (v6-Engine, SMA8/150, 40/60, Slot-Cash-Fallback): CAGR 16.0 / Sortino 1.25 / MaxDD -18.2.
#  Single Source of Truth (B4/B11): Anzeigen leiten sich aus diesen Werten ab.
# ============================================================================
STRAT_NAME = "1xGTAA (defensiv, ungehebelt)"
STRAT_ASCII = "1xGTAA"                    # ntfy-Titel (ASCII!)
STRAT_KEY  = "1xgtaa"
REBALANCE_LABEL = "Cooldown-Modell (taeglich, 10-Handelstage-Freeze)"
SIGNAL_CURRENCY_NOTE = "Signale auf zuverlaessigen USD-1x-Kursen (Yahoo); kein Xetra-Lag (B1)."
INFO_FOOTER = "Rotationsstrategie, monatl.-aehnlicher Umschlag. KEINE ANLAGEBERATUNG."
NTFY_MODE = "change"          # 1xGTAA: ntfy nur bei tatsaechlichem Handel (Vergleich mit zuletzt gemeldeter Allokation)

# asset: ticker (Signal, USD/NYSE), leverage (hier 1x), Anzeige, Produkt, ISIN
ASSETS = {
 "NASDAQ100":   dict(ticker="QQQ",  leverage=1, display="Nasdaq 100",
                     product="iShares Nasdaq 100 UCITS", isin="IE00B53SZB19"),
 "EM_SMALLCAP": dict(ticker="EEMS", leverage=1, display="EM Small Caps",
                     product="SPDR MSCI EM Small Cap UCITS", isin="IE00B48X4842"),
 # EMU Value: EXAKTES Asset = Amundi MSCI EMU Value (AW1T.DE, EUR) -> per fx nach
 # USD (== Backtest-Reihe EMU_VALUE_USD). Xetra-Kurs wird auf das NYSE-Gitter
 # ge-ffill't -> ein evtl. 1-Tages-Lag verzoegert NICHT das ganze Signal (B1).
 "EMU_VALUE":   dict(ticker="AW1T.DE", fx="EURUSD=X", leverage=1, display="EMU Value",
                     product="Amundi MSCI EMU Value UCITS", isin="LU1598690169"),
 "BONDS_7_10":  dict(ticker="IEF",  leverage=1, display="US-Treasury 7-10y",
                     product="iShares $ Treasury 7-10y UCITS", isin="IE00B1FZS798"),
 "GOLD":        dict(ticker="GLD",  leverage=1, display="Gold",
                     product="Xetra-Gold (Alt.: iShares Physical Gold)", isin="DE000A0S9GB0"),
 "COMMODITIES": dict(ticker="DBC",  leverage=1, display="Rohstoffe (breit)",
                     product="WisdomTree Enhanced Commodity UCITS USD Acc (Xetra WTIC; Roll-Optimierung wie DBC)",
                     isin="IE00BYMLZY74"),
 "CASH_USD":    dict(ticker="BIL",  leverage=1, display="Cash / Geldmarkt",
                     product="Xtrackers II USD Overnight Rate Swap 1C (Xetra XFFE; USD-Geldmarkt wie BIL)",
                     isin="LU0321465469"),
}
CFG = dict(mode="gtaa", rebalance="cooldown", cooldown_days=10,
           S=15, L=160, N=2, lookbacks=(1,3,6,12), trend_mode="smax",
           weights=[0.4, 0.6], fallback="slotgate", try_count=3,     # 40/60, Cash-Fallback 40/0 o. 0/60
           prev=dict(until="2026-11-30", S=8, L=150, lookbacks=(1,3,6,12)))   # bis einschl. 30.11.2026 die alten Werte


def cfg_for(day):
    """Zum Tag `day` gueltige Parameter (bis einschl. CFG['prev']['until'] die alten S/L/lookbacks)."""
    p = CFG.get("prev")
    if p and str(day)[:10] <= p["until"]:
        return dict(CFG, S=p["S"], L=p["L"], lookbacks=p["lookbacks"])
    return CFG

# Datenpruefung: Mindestanzahl Kurse je Signalreihe (Strategie braucht SMA/Momentum-Fenster + Reserve). Beginnt eine Reihe
# spaeter als beim letzten Lauf (abgeschnittene Yahoo-Antwort), wird ebenfalls nicht entschieden (Retry).
MIN_ROWS = 400
