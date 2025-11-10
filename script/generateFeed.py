#!/usr/bin/env python3
import json
from datetime import datetime, timezone, timedelta
import re

INPUT_FILE = "data.json"
OUTPUT_FILE = "feed.xml"

# Helper to parse any date string into a datetime with UTC tzinfo
def parse_any_date(s: str) -> datetime:
    s = s.strip()
    # Try RFC 822 first
    try:
        return datetime.strptime(s, "%a, %d %b %Y %H:%M:%S %z").astimezone(timezone.utc)
    except ValueError:
        pass
    # Try ISO format YYYY-MM-DD
    try:
        dt = datetime.strptime(s, "%Y-%m-%d")
        return dt.replace(tzinfo=timezone.utc)
    except ValueError:
        pass
    # Try full month name format "August 22, 2008"
    m = re.match(r"([A-Za-z]+) (\d{1,2}), (\d{4})", s)
    if m:
        month_str, day, year = m.groups()
        dt = datetime.strptime(f"{month_str} {day} {year}", "%B %d %Y")
        return dt.replace(tzinfo=timezone.utc)
    raise ValueError(f"Unknown date format: {s}")

def format_rfc822(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")

def format_duration(total_minutes: int) -> str:
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02}:{minutes:02}:00"

def build_description(ep):
    lines = [f'<a href="{ep["episode_url"]}">{ep["episode_url"]}</a>', "", ep["synopsis"].strip(), ""]
    for act in ep.get("acts", []):
        lines.append(act["number_text"] if act["number_text"] != "Prologue" else "Prologue")
        summary_line = act["summary"].strip()
        if act.get("duration"):
            summary_line += f" ({act['duration']} minutes)"
        if act.get("contributors"):
            summary_line += " by " + ", ".join(act["contributors"])
        lines.append(summary_line)
        lines.append("")
    orig_dt = parse_any_date(ep["original_air_date"])
    lines.append(f"Originally Aired: {orig_dt.strftime('%Y-%m-%d')}")
    return "\n".join(lines)

def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        episodes = json.load(f)

    items = []
    for ep in episodes:
        if not ep.get("download"):
            continue

        # Safely get the latest published date
        latest_pub_dt = max(
            (parse_any_date(d) for d in ep.get("published_dates", [])),
            default=parse_any_date(ep["original_air_date"])
        )

        orig_dt = parse_any_date(ep["original_air_date"])
        is_repeat = latest_pub_dt.year != orig_dt.year
        title_suffix = " - Repeat" if is_repeat else ""

        description = build_description(ep)
        total_minutes = sum((act.get("duration") or 0) for act in ep.get("acts", []))
        padded_number = ep["number"].zfill(4)
        explicit_val = "true" if ep.get("explicit") else "false"

        # Normal episode
        guid = f"{padded_number}-{latest_pub_dt.strftime('%Y%m%d')}"
        item = f"""    <item>
      <title><![CDATA[{ep["number"]}: {ep["title"]}{title_suffix}]]></title>
      <link>{ep["episode_url"]}</link>
      <guid>{guid}</guid>
      <itunes:season>{orig_dt.year}</itunes:season>
      <itunes:episode>{ep["number"]}</itunes:episode>
      <itunes:episodeType>full</itunes:episodeType>
      <itunes:explicit>{explicit_val}</itunes:explicit>
      <description>{description}></description>
      <pubDate>{format_rfc822(latest_pub_dt)}</pubDate>
      <enclosure url="{ep["download"]}" type="audio/mpeg"/>
      <itunes:duration>{format_duration(total_minutes)}</itunes:duration>"""
        if ep.get("image") and ep["image"].get("url"):
            item += f'\n      <itunes:image href="{ep["image"]["url"]}"/>'
        item += "\n    </item>"
        items.append(item)

        # Clean episode
        if ep.get("download_clean"):
            guid_clean = f"{padded_number}-{latest_pub_dt.strftime('%Y%m%d')}-C"
            item_clean = f"""    <item>
      <title><![CDATA[{ep["number"]}: {ep["title"]}{title_suffix} (Clean)]]></title>
      <link>{ep["episode_url"]}</link>
      <guid>{guid_clean}</guid>
      <itunes:season>{orig_dt.year}</itunes:season>
      <itunes:episode>{ep["number"]}</itunes:episode>
      <itunes:episodeType>full</itunes:episodeType>
      <itunes:explicit>clean</itunes:explicit>
      <description>{description}></description>
      <pubDate>{format_rfc822(latest_pub_dt)}</pubDate>
      <enclosure url="{ep["download_clean"]}" type="audio/mpeg"/>
      <itunes:duration>{format_duration(total_minutes)}</itunes:duration>"""
            if ep.get("image") and ep["image"].get("url"):
                item_clean += f'\n      <itunes:image href="{ep["image"]["url"]}"/>'
            item_clean += "\n    </item>"
            items.append(item_clean)

    # Sort by pubDate descending
    items.sort(key=lambda x: parse_any_date(re.search(r"<pubDate>(.*?)</pubDate>", x).group(1)), reverse=True)

    rss_header = """<?xml version="1.0" ?>
<rss xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" version="2.0">
  <channel>
    <title>That American Archive</title>
    <link>https://www.thisamericanlife.org</link>
    <description>Autogenerated feed of the This American Life archive with explicit and clean episodes.</description>
    <language>en</language>
    <copyright>Copyright © Ira Glass / This American Life</copyright>
    <itunes:image href="https://i.imgur.com/pTMCfn9.png"/>"""

    rss_footer = "  </channel>\n</rss>"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(rss_header + "\n")
        f.write("\n".join(items) + "\n")
        f.write(rss_footer + "\n")

if __name__ == "__main__":
    main()
