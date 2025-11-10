#!/usr/bin/env python3
import os
import json
from datetime import datetime, timezone, timedelta
from bs4 import BeautifulSoup
import requests
import feedparser
import re
import time

HEADERS = {"User-Agent": "Mozilla/5.0"}
OFFICIAL_RSS = "https://thisamericanlife.org/podcast/rss.xml"
DELAY = 1
OUTPUT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data.json")
DEFAULT_NUM_EPISODES = 1

ACT_WORDS = {
    "Prologue": 0, "One": 1, "Two": 2, "Three": 3, "Four": 4,
    "Five": 5, "Six": 6, "Seven": 7, "Eight": 8, "Nine": 9, "Ten": 10
}

def parse_any_date(s: str) -> datetime:
    """Return a UTC datetime at midnight for multiple string formats."""
    dt = None
    for fmt in ("%Y-%m-%d", "%a, %d %b %Y %H:%M:%S %z", "%B %d, %Y"):
        try:
            dt = datetime.strptime(s, fmt)
            break
        except ValueError:
            continue
    if dt is None:
        raise ValueError(f"Unknown date format: {s}")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)

def format_rfc822(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S %z")

def format_duration(total_minutes: int) -> str:
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours:02}:{minutes:02}:00"

def fetch_episode_page(url: str):
    try:
        r = requests.get(url, headers=HEADERS)
        r.raise_for_status()
        time.sleep(DELAY)
        return BeautifulSoup(r.text, "html.parser")
    except requests.RequestException:
        return None

def scrape_episode(url: str):
    soup = fetch_episode_page(url)
    if not soup:
        return None

    title = soup.select_one("h1").get_text(strip=True) if soup.select_one("h1") else ""
    number = soup.select_one(".field-name-field-episode-number .field-item")
    number = number.get_text(strip=True) if number else ""
    original_air_date_elem = soup.select_one(".field-name-field-radio-air-date .date-display-single")
    original_air_date = original_air_date_elem.get_text(strip=True) if original_air_date_elem else ""
    synopsis_elem = soup.select_one(".field-name-body .field-item")
    synopsis = synopsis_elem.get_text(strip=True) if synopsis_elem else ""

    download_elem = soup.select_one("li.download a")
    download = download_elem["href"] if download_elem else None
    if not download:
        return None

    clean_elem = soup.select_one(".field-name-field-notes a[href*='/clean/']")
    download_clean = clean_elem["href"] if clean_elem else None
    explicit = bool(download_clean)

    img_elem = soup.select_one("figure.tal-episode-image img")
    image_url = img_elem["src"] if img_elem else None
    credit_elem = soup.select_one("figure.tal-episode-image .credit a")
    image_credit = credit_elem.get_text(strip=True) if credit_elem else None

    acts = []
    for act in soup.select("article.node-act"):
        label_elem = act.select_one(".field-name-field-act-label .field-item")
        act_title_elem = act.select_one("h2.act-header a")
        act_title = act_title_elem.get_text(strip=True) if act_title_elem else ""
        is_prologue = "prologue" in act_title.lower()
        if not label_elem and not is_prologue:
            continue
        if is_prologue:
            act_number = 0
            number_text = "Prologue"
        else:
            word = label_elem.get_text(strip=True).replace("Act ", "").replace("Part ", "").strip()
            act_number = ACT_WORDS.get(word, int(word) if word.isdigit() else 0)
            number_text = f"Act {word}"
        act_summary_elem = act.select_one(".field-name-body .field-item")
        act_summary_raw = act_summary_elem.get_text(" ", strip=True) if act_summary_elem else ""
        duration_match = re.search(r"\((\d+)\s*minutes?\)", act_summary_raw)
        duration = int(duration_match.group(1)) if duration_match else None
        act_summary = re.sub(r"\s*\(\d+\s*minutes?\)", "", act_summary_raw).strip()
        contributors = [a.get_text(strip=True) for div in act.select("div.field-name-field-contributor") for a in div.select("a")]
        full_title = act_title if is_prologue else f"{number_text}: {act_title}"
        acts.append({
            "number": act_number,
            "number_text": number_text,
            "title": full_title,
            "summary": act_summary,
            "duration": duration,
            "contributors": contributors
        })

    return {
        "title": title,
        "number": number,
        "original_air_date": original_air_date,
        "episode_url": url,
        "explicit": explicit,
        "synopsis": synopsis,
        "download": download,
        "download_clean": download_clean,
        "image": {"url": image_url, "credit": image_credit},
        "acts": acts,
        "published_dates": [original_air_date] if original_air_date else []
    }

def update_published_dates(episodes):
    feed = feedparser.parse(OFFICIAL_RSS)
    for item in feed.entries:
        url = item.link
        pub_date = item.get("published") or item.get("pubDate")
        if not pub_date:
            continue
        try:
            dt = parse_any_date(pub_date)
        except ValueError:
            # fallback if RSS feed uses full month names
            dt = parse_any_date(pub_date[:25])
        pub_str = dt.strftime("%Y-%m-%d")
        existing = next((ep for ep in episodes if ep["episode_url"] == url), None)
        if existing and pub_str not in existing["published_dates"]:
            existing["published_dates"].append(pub_str)

def build_description(ep):
    lines = [f'<a href="{ep["episode_url"]}">{ep["episode_url"]}</a>', "", ep["synopsis"].strip(), ""]
    for act in ep.get("acts", []):
        lines.append(act["number_text"] if act["number_text"] != "Prologue" else "Prologue")
        summary_line = act["summary"]
        if act.get("duration"):
            summary_line += f" ({act['duration']} minutes)"
        if act.get("contributors"):
            summary_line += " by " + ", ".join(act["contributors"])
        lines.append(summary_line)
        lines.append("")
    if ep.get("original_air_date"):
        try:
            dt = parse_any_date(ep["original_air_date"])
            lines.append(f"Originally Aired: {dt.strftime('%Y-%m-%d')}")
        except Exception:
            lines.append(f"Originally Aired: {ep['original_air_date']}")
    return "\n".join(lines)

def main():
    scrape_mode = os.environ.get("SCRAPE_MODE", "latest").lower()
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            episodes = json.load(f)
    except FileNotFoundError:
        episodes = []

    feed = feedparser.parse(OFFICIAL_RSS)

    if scrape_mode == "all":
        entries_to_scrape = feed.entries
    elif scrape_mode == "latest":
        entries_to_scrape = feed.entries[:DEFAULT_NUM_EPISODES]
    else:
        try:
            n = int(scrape_mode)
            entries_to_scrape = feed.entries[:n]
        except ValueError:
            entries_to_scrape = feed.entries[:DEFAULT_NUM_EPISODES]

    for entry in entries_to_scrape:
        url = entry.link
        if not any(ep["episode_url"] == url for ep in episodes):
            ep_data = scrape_episode(url)
            if ep_data:
                episodes.append(ep_data)

    update_published_dates(episodes)

    for ep in episodes:
        ep["published_dates"] = sorted(ep["published_dates"], key=parse_any_date)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(episodes, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
