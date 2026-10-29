
import json
import urllib.request
from datetime import datetime, timezone

URL = "https://biquote.io/api/EURUSD/ohlc?interval=1m&limit=100"

def main():
    request = urllib.request.Request(
        URL,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        raw = json.loads(response.read().decode("utf-8"))

    if isinstance(raw, dict):
        candles = raw.get("data", raw.get("candles", raw.get("result", [])))
    else:
        candles = raw

    if not isinstance(candles, list):
        raise ValueError("Не удалось распознать формат ответа API")

    closed = [
        c for c in candles
        if isinstance(c, dict) and not c.get("isOpen", False)
    ]
    closed.sort(key=lambda c: c.get("openTime", 0))

    print("Время проверки:", datetime.now(timezone.utc).isoformat())
    print("Закрытых свечей:", len(closed))

    def number(c, *keys):
        for key in keys:
            if key in c:
                return float(c[key])
        raise KeyError(f"Нет поля {keys}")

    for horizon in (1, 2, 3):
        total = 0
        correct = 0

        for i in range(len(closed) - horizon):
            current = closed[i]
            future = closed[i + horizon]

            o = number(current, "open", "o")
            cl = number(current, "close", "c")
            future_o = number(future, "open", "o")
            future_c = number(future, "close", "c")

            predicted = (cl > o) - (cl < o)
            actual = (future_c > future_o) - (future_c < future_o)

            if predicted == 0 or actual == 0:
                continue

            total += 1
            correct += predicted == actual

        pct = 100 * correct / total if total else 0
        print(f"{horizon} мин: {correct}/{total} = {pct:.1f}%")

    with open("report.json", "w", encoding="utf-8") as f:
        json.dump({
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "closed_candles": len(closed)
        }, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
