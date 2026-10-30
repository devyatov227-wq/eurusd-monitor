
import json
import urllib.request
from datetime import datetime, timezone

URL = "https://biquote.io/api/EURUSD/ohlc?interval=1m&limit=100"


def main():
    req = urllib.request.Request(
        URL,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        raw = json.loads(response.read().decode("utf-8"))

    if not isinstance(raw, dict):
        raise ValueError("Ответ API должен быть JSON-объектом")

    candles = raw.get("bars", [])

    if not isinstance(candles, list):
        raise ValueError("Поле bars отсутствует или имеет неверный формат")

    candles = [
        c for c in candles
        if isinstance(c, dict)
        and c.get("isOpen") is False
        and all(k in c for k in ("openTime", "open", "close"))
    ]

    candles.sort(key=lambda c: c["openTime"])

    print("=" * 45)
    print("EUR/USD MONITOR")
    print("Время UTC:", datetime.now(timezone.utc).isoformat())
    print("Всего получено свечей:", len(raw.get("bars", [])))
    print("Закрытых свечей:", len(candles))
    print("=" * 45)

    def direction(c):
        o = float(c["open"])
        close = float(c["close"])

        if close > o:
            return 1
        if close < o:
            return -1
        return 0

    results = {}

    for horizon in (1, 2, 3):
        correct = 0
        total = 0

        for i in range(len(candles) - horizon):
            predicted = direction(candles[i])
            actual = direction(candles[i + horizon])

            if predicted == 0 or actual == 0:
                continue

            total += 1

            if predicted == actual:
                correct += 1

        accuracy = (
            round(correct / total * 100, 1)
            if total else None
        )

        results[f"{horizon}_candle_ahead"] = {
            "correct": correct,
            "total": total,
            "direction_match_percent": accuracy
        }

        print(
            f"Через {horizon} свечу: "
            f"{correct}/{total}, "
            f"совпадение направлений: {accuracy}%"
        )

    report = {
        "symbol": raw.get("symbol", "EURUSD"),
        "interval": raw.get("interval", "1m"),
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "closed_candles": len(candles),
        "results": results
    }

    with open("report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("=" * 45)
    print("Отчёт сохранён: report.json")


if __name__ == "__main__":
    main()
