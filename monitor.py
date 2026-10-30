
import json
import os
import urllib.request
from datetime import datetime, timezone

URL = "https://biquote.io/api/EURUSD/ohlc?interval=1m&limit=100"
HISTORY_FILE = "history.json"
REPORT_FILE = "report.json"
MAX_HISTORY = 10000


def main():
    req = urllib.request.Request(
        URL, headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        raw = json.loads(response.read().decode("utf-8"))

    if not isinstance(raw, dict) or not isinstance(raw.get("bars"), list):
        raise ValueError("Неожиданный формат ответа API")

    incoming = [
        c for c in raw["bars"]
        if isinstance(c, dict)
        and c.get("isOpen") is False
        and all(k in c for k in ("openTime", "open", "close"))
    ]

    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = {"symbol": "EURUSD", "interval": "1m", "candles": []}

    candles_by_time = {
        c["openTime"]: c
        for c in history.get("candles", [])
        if isinstance(c, dict) and "openTime" in c
    }

    for candle in incoming:
        candles_by_time[candle["openTime"]] = candle

    candles = sorted(
        candles_by_time.values(),
        key=lambda c: c["openTime"]
    )[-MAX_HISTORY:]

    history = {
        "symbol": "EURUSD",
        "interval": "1m",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "candles": candles
    }

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    def direction(c):
        o = float(c["open"])
        close = float(c["close"])
        return (close > o) - (close < o)

    results = {}

    for horizon in (1, 2, 3):
        correct = total = 0

        for i in range(len(candles) - horizon):
            predicted = direction(candles[i])
            actual = direction(candles[i + horizon])

            if predicted == 0 or actual == 0:
                continue

            total += 1
            correct += int(predicted == actual)

        results[f"{horizon}_candle_ahead"] = {
            "correct": correct,
            "total": total,
            "direction_match_percent": (
                round(correct / total * 100, 1) if total else None
            )
        }

    report = {
        "symbol": "EURUSD",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "new_candles_received": len(incoming),
        "historical_candles": len(candles),
        "results": results
    }

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("Новых свечей:", len(incoming))
    print("Всего в истории:", len(candles))
    for period, result in results.items():
        print(period, result)


if __name__ == "__main__":
    main()
