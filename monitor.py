#!/usr/bin/env python3
"""EUR/USD collector + simple historical strategy test. No trades are placed."""
import json
import os
import urllib.request
from datetime import datetime, timezone

URL = os.getenv("EURUSD_API_URL", "https://biquote.io/api/EURUSD/ohlc?interval=1m&limit=100")
HISTORY_FILE, REPORT_FILE = "history.json", "report.json"
MAX_HISTORY = 10000
EMA_FAST, EMA_SLOW, RSI_PERIOD = 9, 21, 14
RSI_BUY_MIN, RSI_SELL_MAX = 52.0, 48.0
PAYOUT = 0.96  # Illustrative only; confirm actual platform payout.


def now():
    return datetime.now(timezone.utc).isoformat()


def fetch_bars():
    req = urllib.request.Request(URL, headers={"User-Agent": "EURUSD-monitor/2.1"})
    with urllib.request.urlopen(req, timeout=20) as response:
        if response.status != 200:
            raise RuntimeError(f"API HTTP {response.status}")
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("bars"), list):
        raise ValueError("Unexpected API format: expected object containing bars[]")
    unique = {}
    for x in payload["bars"]:
        if not isinstance(x, dict) or x.get("isOpen") is not False:
            continue
        try:
            c = {
                "openTime": str(x["openTime"]),
                "open": float(x["open"]), "high": float(x["high"]),
                "low": float(x["low"]), "close": float(x["close"]),
                "volume": float(x.get("volume", 0) or 0),
                "tickVolume": int(x.get("tickVolume", 0) or 0),
                "isOpen": False,
            }
            if min(c["open"], c["high"], c["low"], c["close"]) > 0:
                unique[c["openTime"]] = c
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(unique.values(), key=lambda c: c["openTime"])


def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    with open(HISTORY_FILE, encoding="utf-8") as f:
        obj = json.load(f)
    if not isinstance(obj, dict) or not isinstance(obj.get("candles"), list):
        raise ValueError("history.json has an invalid structure")
    return obj["candles"]


def save_history(candles):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "symbol": "EURUSD", "interval": "1m",
            "updated_at": now(), "candles": candles[-MAX_HISTORY:]
        }, f, ensure_ascii=False, indent=2)


def ema(values, period):
    out = [None] * len(values)
    if len(values) < period:
        return out
    prev = sum(values[:period]) / period
    out[period - 1] = prev
    alpha = 2 / (period + 1)
    for i in range(period, len(values)):
        prev = values[i] * alpha + prev * (1 - alpha)
        out[i] = prev
    return out


def rsi(values, period=14):
    out = [None] * len(values)
    if len(values) <= period:
        return out
    changes = [values[i] - values[i - 1] for i in range(1, period + 1)]
    gain = sum(max(x, 0) for x in changes) / period
    loss = sum(max(-x, 0) for x in changes) / period

    def calc(g, l):
        return 100.0 if l == 0 and g > 0 else 50.0 if l == 0 else 100 - 100 / (1 + g / l)

    out[period] = calc(gain, loss)
    for i in range(period + 1, len(values)):
        change = values[i] - values[i - 1]
        gain = (gain * (period - 1) + max(change, 0)) / period
        loss = (loss * (period - 1) + max(-change, 0)) / period
        out[i] = calc(gain, loss)
    return out


def direction_stats(candles, horizon):
    correct = total = 0
    for i in range(len(candles) - horizon):
        a = candles[i]["close"] - candles[i]["open"]
        b = candles[i + horizon]["close"] - candles[i + horizon]["open"]
        if a == 0 or b == 0:
            continue
        total += 1
        correct += int((a > 0) == (b > 0))
    return {
        "correct": correct, "total": total,
        "direction_match_percent": round(100 * correct / total, 2) if total else None
    }


def backtest(candles):
    closes = [c["close"] for c in candles]
    fast, slow, rsis = ema(closes, EMA_FAST), ema(closes, EMA_SLOW), rsi(closes, RSI_PERIOD)
    trades = []
    for i in range(len(candles) - 1):
        if fast[i] is None or slow[i] is None or rsis[i] is None:
            continue
        signal = "BUY" if fast[i] > slow[i] and rsis[i] >= RSI_BUY_MIN else (
            "SELL" if fast[i] < slow[i] and rsis[i] <= RSI_SELL_MAX else None
        )
        if signal is None:
            continue
        nxt = candles[i + 1]
        entry, exit_price = nxt["open"], nxt["close"]
        outcome = "DRAW" if exit_price == entry else (
            "WIN" if (signal == "BUY") == (exit_price > entry) else "LOSS"
        )
        trades.append({
            "signal_time": candles[i]["openTime"], "entry_time": nxt["openTime"],
            "signal": signal, "rsi": round(rsis[i], 2),
            "entry": entry, "exit": exit_price, "outcome": outcome
        })

    wins = sum(t["outcome"] == "WIN" for t in trades)
    losses = sum(t["outcome"] == "LOSS" for t in trades)
    draws = sum(t["outcome"] == "DRAW" for t in trades)
    decided = wins + losses
    return {
        "status": "ok" if len(candles) >= 23 else "insufficient_data",
        "strategy": "EMA 9/21 trend filter + RSI 14 (BUY >=52, SELL <=48)",
        "entry_exit": "Signal after candle close; enter next candle open; exit next candle close",
        "trades": len(trades), "wins": wins, "losses": losses, "draws": draws,
        "win_rate_percent_excluding_draws": round(100 * wins / decided, 2) if decided else None,
        "illustrative_payout": PAYOUT,
        "illustrative_breakeven_win_rate_percent": round(100 / (1 + PAYOUT), 2),
        "estimated_net_units_per_1_unit_stake": round(wins * PAYOUT - losses, 4),
        "last_10_trades": trades[-10:],
        "warning": "Toy historical test only: ignores spread, fees, slippage, delays and platform settlement. Not a live signal or proof of profitability."
    }


def main():
    old = load_history()
    old_map = {str(c["openTime"]): c for c in old if isinstance(c, dict) and "openTime" in c}
    fetched = fetch_bars()
    fresh_map = {c["openTime"]: c for c in fetched}
    added = sum(ts not in old_map for ts in fresh_map)
    merged = dict(old_map)
    merged.update(fresh_map)
    candles = sorted(merged.values(), key=lambda c: c["openTime"])[-MAX_HISTORY:]
    save_history(candles)

    report = {
        "symbol": "EURUSD", "interval": "1m", "checked_at": now(),
        "api_closed_unique_candles_received": len(fetched),
        "new_unique_candles_added": added,
        "historical_unique_candles_after_update": len(candles),
        "direction_match_baseline": {
            f"{h}_candle_ahead": direction_stats(candles, h) for h in (1, 2, 3)
        },
        "strategy_backtest": backtest(candles)
    }
    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("EUR/USD MONITOR")
    print("API closed unique candles:", len(fetched))
    print("New unique candles added:", added)
    print("Total unique historical candles:", len(candles))
    print("Strategy backtest:", json.dumps(report["strategy_backtest"], ensure_ascii=False))
    print("Report saved:", REPORT_FILE)


if __name__ == "__main__":
    main()
