import json
import urllib.request
from datetime import datetime, timezone

URL = "https://biquote.io/api/EURUSD/ohlc?interval=1m&limit=100"

def main():
    req = urllib.request.Request(
        URL, headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = json.loads(response.read().decode("utf-8"))

    candles = raw
    if isinstance(raw, dict):
        candles = raw.get("data", raw.get("candles", raw.get("result", [])))

    if not isinstance(candles, list):
        raise ValueError("Неизвестный формат данных API")

    candles = [
        c for c in candles
        if isinstance(c, dict) and not c.get("isOpen", False)
    ]
    candles.sort(key=lambda c: c.get("openTime", 0))

    print("Проверка UTC:", datetime.now(timezone.utc).isoformat())
    print("Закрытых свечей:", len(candles))

    def price(c, key):
        return float(c[key])

    results = {}

    for horizon in (1, 2, 3):
        correct = total = 0

        for i in range(len(candles) - horizon):
            current = candles[i]
            future = candles[i + horizon]

            predicted = (price(current, "close") > price(current, "open")) - (
                price(current, "close") < price(current, "open")
            )
            actual = (price(future, "close") > price(future, "open")) - (
                price(future, "close") < price(future, "open")
            )

            if predicted == 0 or actual == 0:
                continue

            total += 1
            correct += int(predicted == actual)

        accuracy = round(100 * correct / total, 1) if total else None
        results[f"{horizon}_minute"] = {
            "correct": correct,
            "total": total,
            "accuracy_percent": accuracy
        }
        print(f"{horizon} мин: {correct}/{total}, точность: {accuracy}%")

    with open("report.json", "w", encoding="utf-8") as f:
        json.dump({
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "closed_candles": len(candles),
            "results": results
        }, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
