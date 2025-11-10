#!/usr/bin/env python3
import json
from datetime import datetime
from pathlib import Path

# Working directory = repo root
repo_root = Path.cwd()
data_file = Path(__file__).parent.parent / "data.json"
md_file = Path(__file__).parent.parent / "episodes.md"

if not data_file.exists():
    print(f"Error: {data_file} not found")
    exit(1)

with open(data_file, encoding="utf-8") as f:
    episodes = json.load(f)

# Sort ascending by original_air_date
episodes.sort(
    key=lambda ep: datetime.strptime(
        ep["original_air_date"].split(" +")[0], "%a, %d %b %Y %H:%M:%S"
    )
)

with open(md_file, "w", encoding="utf-8") as out:
    out.write("Title|Release Date|Download|Clean|Segments|\n")
    out.write("---|:-:|:-:|:-:|-\n")

    for ep in episodes:
        number = ep.get("number")
        title = ep.get("title")
        url = ep.get("episode_url")
        download = ep.get("download")
        download_clean = ep.get("download_clean")
        air_date = datetime.strptime(
            ep["original_air_date"].split(" +")[0], "%B %d, %Y"
        ).strftime("%Y-%m-%d")  # yyyy-mm-dd
        acts = ep.get("acts", [])
        act_titles = "; ".join(act.get("title") for act in acts)
        clean_link = f"[dl]({download_clean})" if download_clean else "-"

        out.write(
            f"[{number}: {title}]({url})|{air_date}|[dl]({download})|{clean_link}|{act_titles}\n"
        )

print(f"Markdown generated at {md_file.resolve()}")
