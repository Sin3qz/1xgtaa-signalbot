import traceback

from strategies.runner import run_strategy, commit_notify_state, mark_error
from strategies.constants import STRAT_ASCII

try:
    from send_ntfy import send_ntfy
except Exception:
    def send_ntfy(_title, _msg, tags=None):
        print("send_ntfy module not available.")
        return False


def save_text(text):
    if text:
        with open("message.txt", "w", encoding="utf-8") as f:
            f.write(text)


TITLES = {"BUY": f"{STRAT_ASCII}: BUY - neu investieren", "SELL": f"{STRAT_ASCII}: SELL - raus in Cash",
          "SWITCH": f"{STRAT_ASCII}: SWITCH - Umschichtung"}


def main():
    # signal: None = nur Discord-Status; BUY/SELL/SWITCH = tatsaechlicher Handel -> ntfy; "Error"
    signal, ntfy_text, discord_text = run_strategy()
    save_text(discord_text)
    if signal in TITLES:
        ok = False
        title = TITLES[signal] + (" (verspaetet)" if "verspätet" in (ntfy_text or "")[:300] else "")
        try:
            ok = send_ntfy(title, ntfy_text or discord_text)
        except Exception as e:
            print(f"ntfy send raised (ignored): {e}")
        if ok or ok is None:           # None = kein NTFY_TOPIC konfiguriert -> nicht endlos wiederholen
            commit_notify_state()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        save_text("Error\n\n" + "".join(traceback.format_exception(e)))
        try:
            mark_error(e)
        except Exception:
            pass
