# -*- coding: utf-8 -*-
"""
1xGTAA — LIVE-Runner. Strategie-Parameter und -Berechnung UNVERAENDERT (gtaa_botcore.py,
constants.py: Top-2, SMA8 > SMA150, Momentum 1/3/6/9, 40/60, Slot-Cash-Fallback, 10-Tage-Freeze).

Geaendert (29.09.2026):
  * ntfy nur bei tatsaechlichem Handel, Vergleich mit der zuletzt GEMELDETEN Allokation
    (notify_state_1xgtaa.json) -> keine Doppelmeldungen an Wochenenden/Feiertagen/Retries,
    kein verpasster Wechsel, wenn Daten verspaetet kommen; nur mit frischen Daten.
  * Handytaugliche, schmale Tabellen (Discord-Codeblock <= ~30 Zeichen; ntfy ohne Codeblock).
  * Dashboard: Zeitbalken zeigt Platz 1 (gehaltenes Asset mit hoechstem Momentum).

Vertrag fuer main.py:  run_strategy() -> (signal, ntfy_text, discord_text)
"""
import time

import numpy as np
import pandas as pd

from . import common as U
from .constants import (STRAT_NAME, STRAT_KEY, ASSETS, CFG, REBALANCE_LABEL, INFO_FOOTER, MIN_ROWS)
from . import gtaa_botcore as B

STATUS_FILE = f"status_{STRAT_KEY}.json"
NOTIFY_FILE = f"notify_state_{STRAT_KEY}.json"
HISTORY_FILE = f"history_{STRAT_KEY}.txt"
ASSET_LIST = list(ASSETS.keys())
PENDING_STATE = {}
SHORT = {"NASDAQ100": "Nasdaq", "EM_SMALLCAP": "EM Small", "EMU_VALUE": "EMU Val", "BONDS_7_10": "UST 7-10",
         "GOLD": "Gold", "COMMODITIES": "Rohstoff", "CASH_USD": "Cash$"}


def mark_error(e):
    """Lauf fehlgeschlagen: Status als needsRetry markieren (letzter gueltiger Stand bleibt)."""
    U.mark_status_error(STATUS_FILE, e)


def commit_notify_state():
    if PENDING_STATE:
        U.save_json(NOTIFY_FILE, dict(PENDING_STATE))


# ==========================================================================
#  DATEN (unveraendert zur verifizierten Version)
# ==========================================================================
def _fetch(ticker):
    return U.fetch_close(ticker, CFG.get("try_count", 3))


GRID_START = "1999-01-04"


def _load_raw(fetch=_fetch):
    fx_cache, raw = {}, {}
    for asset, meta in ASSETS.items():
        s = fetch(meta["ticker"])
        fx = meta.get("fx")
        if fx:                                   # EUR-Reihe -> USD (wie Backtest EMU_VALUE_USD)
            if fx not in fx_cache:
                fx_cache[fx] = fetch(fx)
            s = (s * fx_cache[fx].reindex(s.index).ffill()).dropna()
        raw[asset] = s
    for fx, s in fx_cache.items():            # FX nur fuer die Datenpruefung (Frische des Wechselkurses)
        raw[f"FX:{fx}"] = s
    return raw


def closes_on_grid(raw):
    """NYSE-Handelstags-Gitter wie im Backtest (gtaa_clean = exakt NYSE-Sitzungen). Fehlt bei Yahoo ein
    einzelner Tag, bleibt die Zeile erhalten (letzter Kurs fortgeschrieben) -> der 10-Tage-Cooldown zaehlt
    jeden Handelstag. Fehlt bei einem US-Titel der JUENGSTE Tag, endet das Gitter am letzten gemeinsamen
    Tag (keine Entscheidung auf fortgeschriebenen Kursen)."""
    us = [raw[a] for a in ASSET_LIST if not ASSETS[a].get("fx")]
    grid = U.build_grid(GRID_START, us_series=us)
    out = pd.DataFrame({a: U.oncal(raw[a], grid) for a in ASSET_LIST})
    return out.dropna(how="any"), grid


def _load_closes(fetch=_fetch):
    raw = _load_raw(fetch)
    closes, _ = closes_on_grid(raw)
    return closes, raw


# ==========================================================================
#  Anzeige
# ==========================================================================
def _alloc_lines(alloc):
    if not alloc:
        return ["💵 CASH — 100 % nicht investiert"]
    lines, tot = [], 0.0
    for a, w in sorted(alloc.items(), key=lambda kv: -kv[1]):
        tot += w
        lines.append(f"• {U.w0(w):>4}  {ASSETS[a]['display']}")
    if 1 - tot > 0.005:
        lines.append(f"• {U.w0(1 - tot):>4}  Cash (Fallback)")
    return lines


def _rows(alloc, ind, i):
    mom, rankv = ind["mom"], ind["rank_val"]
    order = sorted(ASSET_LIST, key=lambda a: mom[a].iloc[i] if pd.notna(mom[a].iloc[i]) else -1e9, reverse=True)
    rows = []
    for a in order:
        mv, rv = mom[a].iloc[i], rankv[a].iloc[i]
        tr = bool(ind["trend"][a].iloc[i]) if pd.notna(ind["trend"][a].iloc[i]) else False
        st = U.w0(alloc[a]) if a in alloc else ("ok" if (tr and mv == mv and mv > 0) else "–")
        rows.append([SHORT.get(a, a[:8]), U.pct0(mv), U.pct0(rv), st])
    return order, rows


def _lead(alloc, ind, k):
    """Platz 1 = gehaltenes Asset mit dem hoechsten Momentum am Tag k."""
    if not alloc:
        return "CASH"
    return max(alloc, key=lambda a: ind["mom"][a].iloc[k] if pd.notna(ind["mom"][a].iloc[k]) else -1e9)


def _change_type(prev, cur):
    if prev == cur:
        return None
    if cur == "CASH":
        return "SELL"
    if prev == "CASH":
        return "BUY"
    return "SWITCH"


def _messages(c):
    L = []
    if c["signal"]:
        L += [{"BUY": "🟢 BUY — neu investieren", "SELL": "🔴 SELL — raus in Cash",
               "SWITCH": "🔄 UMSCHICHTUNG — neue Allokation"}[c["signal"]],
              (f"(verspätet; Signal: Schluss {U.de(c['change_date'])}, regulär {U.de(c['trade'])} — heute {U.de(c['today'])} handeln)"
               if c["late"] else f"(Signal: Schluss {U.de(c['change_date'])}, handeln am {U.de(c['trade'])})"), ""]
    elif c["pending"]:
        L += [f"⏳ Wechsel erkannt (Signal: Schluss {U.de(c['change_date'])}) — handeln am {U.de(c['pending'])}; "
              f"ntfy kommt an diesem Handelstag.", ""]
    L += [f"📊 {STRAT_NAME}"] + _alloc_lines(c["alloc"])
    L += [f"Cooldown: {c['cd']} Handelstage gesperrt" if c["cd"] > 0 else "Cooldown: frei (Wechsel möglich)"]
    if c["no_new_day"]:
        L += [f"ℹ️ Kein neuer US-Handelstag seit {U.de_short(c['asof'])} (Wochenende/Feiertag)"]
    order, rows = _rows(c["alloc"], c["ind"], c["i"])
    tab = U.table(["Asset", "MoM", f"SMA", "Ziel"], rows, "lrrr")
    legend = [f"MoM = Summe 1/3/6/9 M · SMA = SMA{CFG['S']}/SMA{CFG['L']}", "ok = qualifiziert, – = raus"]
    disc = L + ["", f"Signale (1x-USD, Stand {U.de_short(c['asof'])}):", "```"] + tab + ["```"] + legend
    ntfy = L + ["", f"Signale (Stand {U.de_short(c['asof'])}):"] + [f"{r[0]}: MoM {r[1]}, SMA {r[2]}, {r[3]}" for r in rows]
    tail = []
    if c["stale"]:
        tail += ["", "⚠️ Kursdaten evtl. veraltet — Retry läuft; ntfy erst mit frischen Daten."]
    if c["warns"]:
        tail += ["", "⚠️ Datenprüfung:"] + [f"• {x}" for x in c["warns"][:6]]
    tail += ["", INFO_FOOTER]
    return "\n".join(ntfy + tail), "\n".join(disc + tail)


# ==========================================================================
#  HAUPTFUNKTION
# ==========================================================================
def run_strategy(closes=None, raw=None, write_files=True):
    if closes is None:
        try:
            closes, raw = _load_closes()
        except Exception as e:
            mark_error(e)
            return ("Error", None, f"{STRAT_NAME}: Daten konnten nicht geladen werden: {e}" + "\n" + U.ERROR_HINT)

    # ---- Datenpruefung VOR der Berechnung: Datum des letzten ECHTEN Kurses je Reihe (nicht der
    #      fortgeschriebene Gitterwert), fehlende Handelstage, Tagesspruenge > 30 % ----
    exp = U.expected_session_date()
    src = raw if raw is not None else {a: closes[a] for a in ASSET_LIST}
    prev_first = U.load_json(STATUS_FILE).get("firstDates", {})         # Erkennung abgeschnittener Yahoo-Antworten
    grid = pd.DatetimeIndex(closes.index)
    freshness, warns = {}, []
    for a in ASSET_LIST:
        us = not ASSETS[a].get("fx")
        t = ASSETS[a]["ticker"]
        # Xetra (EMU Value): Xetra-Feiertage erlaubt -> frisch, wenn <= 4 Kalendertage alt
        f, last, w = U.check_series(f"{SHORT.get(a, a)} ({t})", src[a], grid, us_market=us,
                                    max_age_days=(None if us else 4), min_rows=MIN_ROWS, prev_first=prev_first.get(t))
        freshness[a] = {"last": last, "fresh": bool(f)}
        warns += w
    for k in [k for k in src if str(k).startswith("FX:")]:          # EURUSD=X separat pruefen
        fx = k[3:]
        f, last, w = U.check_series(fx, src[k], grid, us_market=False, max_age_days=4, min_rows=MIN_ROWS,
                                    prev_first=prev_first.get(fx))
        freshness[fx] = {"last": last, "fresh": bool(f)}
        warns += w
    stale = not all(f["fresh"] for f in freshness.values())
    warns = sorted(set(warns))

    idx, allocs, cds, ind, rebound = B.compute_series(closes, CFG, live=True)
    sigs = [B.alloc_signature(a) for a in allocs]
    i = len(idx) - 1
    cur = sigs[-1]
    chg = [k for k in range(1, len(sigs)) if sigs[k] != sigs[k - 1]]
    change_date = idx[chg[-1]].date() if chg else idx[0].date()

    # ---- ntfy nur bei tatsaechlichem Handel, nur an NYSE-Handelstagen ----
    today = U.berlin_today()
    trade_c = U.next_session_after(change_date)            # regulaerer Handelstag des juengsten Wechsels
    state = U.load_json(NOTIFY_FILE)
    signal, late, pending = None, False, None
    if not state.get("lastSignature"):
        # Erststart (oder Zustand verloren): Ist der juengste Wechsel noch nicht gehandelt (Handelstag heute oder
        # spaeter), wird mit der Allokation VOR dem Wechsel gestartet -> die Meldung geht normal raus.
        if chg and trade_c is not None and today <= trade_c:
            state = {"lastSignature": sigs[chg[-1] - 1], "init": today.isoformat()}
        else:
            state.update(lastSignature=cur, since=change_date.isoformat(), init=today.isoformat())
            if write_files:
                U.save_json(NOTIFY_FILE, state)
    if state["lastSignature"] != cur and not stale:
        if U.ntfy_allowed(today) and today >= trade_c:
            signal = _change_type(state["lastSignature"], cur)
            late = today > trade_c
            state.update(lastSignature=cur, since=change_date.isoformat(), sentOn=today.isoformat())
            PENDING_STATE.clear(); PENDING_STATE.update(state)
        else:                                               # Wochenende/Feiertag -> ntfy am naechsten Handelstag
            pending = trade_c if (trade_c and trade_c >= today) else U.next_session_after(today)

    ctx = dict(signal=signal, alloc=allocs[-1], cd=int(cds[-1]), ind=ind, i=i, asof=idx[i].date(),
               change_date=change_date, trade=trade_c, late=late, today=today, pending=pending, stale=stale, warns=warns,
               no_new_day=(not stale) and idx[i].date() < U.berlin_yesterday())
    ntfy_text, disc_text = _messages(ctx)

    order, rows = _rows(allocs[-1], ind, i)
    tail = range(max(0, len(idx) - 400), len(idx))
    status = {
        "strategy": STRAT_NAME, "name": "1xGTAA", "key": STRAT_KEY,
        "updated": pd.Timestamp.now(tz=U.TZ).isoformat(),
        "rebalance": CFG["rebalance"], "rebalanceLabel": REBALANCE_LABEL,
        "asOf": idx[i].date().isoformat(), "needsRetry": bool(stale), "dataWarnings": warns,
        "changedToday": signal is not None, "changeType": signal, "cooldown": int(cds[-1]), "late": bool(late),
        "pendingTrade": pending.isoformat() if pending else None,
        "since": change_date.isoformat(), "nextRebalance": None,
        "allocation": [{"asset": a, "display": ASSETS[a]["display"], "weight": round(w, 4), "leverage": ASSETS[a]["leverage"],
                        "product": ASSETS[a]["product"], "isin": ASSETS[a].get("isin", "")}
                       for a, w in sorted(allocs[-1].items(), key=lambda kv: -kv[1])] or
                      [{"asset": "CASH", "display": "Cash", "weight": 1.0, "leverage": 1, "product": "—", "isin": ""}],
        "signals": {a: {"momentum": U.num(ind["mom"][a].iloc[i]),
                        "trend": bool(ind["trend"][a].iloc[i]) if pd.notna(ind["trend"][a].iloc[i]) else None,
                        "rankValue": U.num(ind["rank_val"][a].iloc[i]), "display": ASSETS[a]["display"],
                        "leverage": ASSETS[a]["leverage"]} for a in ASSET_LIST},
        "table": {"head": ["Baustein", "MoM", "Trend", "Ziel"],
                  "note": f"MoM = Summe der 1/3/6/9-Monats-Renditen · Trend = SMA{CFG['S']}/SMA{CFG['L']} − 1 (qualifiziert, wenn > 0 und MoM > 0) · Top-2 40/60",
                  "rows": [[SHORT.get(a, a), U.num(ind["mom"][a].iloc[i]), U.num(ind["rank_val"][a].iloc[i]),
                            U.num(allocs[-1].get(a, 0.0), 4)] for a in order],
                  "kinds": ["text", "spct", "spct", "pct"]},
        "timeline": {"span": "letzte 120 Handelstage (tägliche Entscheidung)",
                     "what": "welches gehaltene Asset auf Platz 1 lag (höchstes Momentum)",
                     "items": [{"date": idx[k].date().isoformat(), "lead": _lead(allocs[k], ind, k), "allocation": sigs[k]}
                               for k in range(max(0, len(idx) - 120), len(idx))]},
        "freshness": freshness,
        "firstDates": U.merge_first(prev_first, {(ASSETS[a]["ticker"] if a in ASSETS else a[3:]): U.first_date(s)
                                              for a, s in src.items()}),
        "history": [{"date": idx[k].date().isoformat(), "allocation": sigs[k]} for k in tail],
    }
    if write_files:
        U.save_json(STATUS_FILE, status)
        try:
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                f.write("date,allocation,cooldown,platz1\n")
                for k in range(len(idx)):
                    if sigs[k] == "CASH" and k < 200:
                        continue
                    f.write(f"{idx[k].date()},{sigs[k]},{cds[k]},{_lead(allocs[k], ind, k)}\n")
        except Exception as e:
            print(f"History-Schreibfehler (ignoriert): {e}")
    return signal, ntfy_text, disc_text
