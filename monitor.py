
import json
import urllib.request
from datetime import datetime, timezone

URL = "https://biquote.io/api/EURUSD/ohlc?interval=1m&limit=5"

def main():
    req = urllib.request.Request(
        URL,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    with urllib.request.urlopen(req, timeout=30) as response:
        body = response.read().decode("utf-8")
        print("HTTP status:", response.status)
        print("Content-Type:", response.headers.get("Content-Type"))

    print("UTC:", datetime.now(timezone.utc).isoformat())
    print("Ответ сервера:")
    print(body[:5000])

    try:
        raw = json.loads(body)
    except json.JSONDecodeError as error:
        print("Ответ не является JSON:", error)
        return

    print("\nТип ответа:", type(raw).__name__)

    if isinstance(raw, dict):
        print("Ключи верхнего уровня:", list(raw.keys()))

        for key, value in raw.items():
            if isinstance(value, list):
                print(f"\nСписок {key}: элементов {len(value)}")
                if value:
                    print("Поля первого элемента:",
                          list(value[0].keys())
                          if isinstance(value[0], dict)
                          else type(value[0]).__name__)
    elif isinstance(raw, list):
        print("Количество элементов:", len(raw))
        if raw and isinstance(raw[0], dict):
            print("Поля первой свечи:", list(raw[0].keys()))

if __name__ == "__main__":
    main()
