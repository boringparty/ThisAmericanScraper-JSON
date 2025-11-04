import json
from datetime import datetime, timezone

def parse_date(d):
    for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(d, fmt)
        except ValueError:
            continue
    return None

def to_rfc822(dt):
    if not dt:
        return None
    dt_utc = dt.astimezone(timezone.utc)
    return dt_utc.strftime("%a, %d %b %Y %H:%M:%S +0000")

with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for ep in data:
    if "original_air_date" in ep and ep["original_air_date"]:
        dt = parse_date(ep["original_air_date"])
        ep["original_air_date"] = to_rfc822(dt) if dt else ep["original_air_date"]

    if "published_dates" in ep:
        normalized = set()
        for d in ep["published_dates"]:
            dt = parse_date(d)
            if dt:
                normalized.add(to_rfc822(dt))
        ep["published_dates"] = sorted(normalized)

with open("data_fixed.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)
