# ============================================================================
#  1xGTAA — defensiv, ungehebelt (7 Bausteine).  Cooldown-Modell (taegliche
#  Entscheidung, 10-Handelstage-Freeze), Top-2 nach Momentum, 40/60-Tilt (P2-UEG).
#  Cash-Fallback per Slot (Dual-Momentum): 40/0 o. 0/60, sonst Cash (strikt).
#  Trend SMA8 > SMA150. Momentum = Summe 1/3/6/9-Monats-Returns. Kein Look-Ahead.
#  Verifiziert (v6-Engine, SMA8/150, 40/60, Slot-Cash-Fallback): CAGR 16.0 / Sortino 1.25 / MaxDD -18.2.
#  Single Source of Truth (B4/B11): Anzeigen leiten sich aus diesen Werten ab.
# ============================================================================
STRAT_NAME = "1xGTAA (defensiv, ungehebelt)"
STRAT_ASCII = "1xGTAA"                    # ntfy-Titel (ASCII!)
STRAT_KEY  = "1xgtaa"
REBALANCE_LABEL = "Cooldown-Modell (taeglich, 10-Handelstage-Freeze)"
SIGNAL_CURRENCY_NOTE = "Signale auf zuverlaessigen USD-1x-Kursen (Yahoo); kein Xetra-Lag (B1)."
INFO_FOOTER = "Rotationsstrategie, monatl.-aehnlicher Umschlag. KEINE ANLAGEBERATUNG."
NTFY_MODE = "change"          # 1xGTAA: ntfy nur bei echtem Wechsel (Cooldown-Modell)
NOTIFY_DAYS = []

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
                     product="Invesco Bloomberg Commodity UCITS", isin="IE00BD6FTQ80"),
 "CASH_USD":    dict(ticker="BIL",  leverage=1, display="Cash / Geldmarkt",
                     product="Xtrackers EUR Overnight Rate (Xeon)", isin="LU0290358497"),
}
CFG = dict(mode="gtaa", rebalance="cooldown", cooldown_days=10,
           S=8, L=150, N=2, lookbacks=(1,3,6,9), trend_mode="smax",
           weights=[0.4, 0.6], fallback="slotgate", try_count=3)   # 40/60, Cash-Fallback 40/0 o. 0/60
