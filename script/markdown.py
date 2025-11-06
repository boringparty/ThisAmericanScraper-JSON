import json
from datetime import datetime
from pathlib import Path

# Paths
repo_root = Path(__file__).parent.parent
data_file = repo_root / "data.json"
md_file = repo_root / "episodes.md"

# Load JSON
with open(data_file) as f:
    episodes = json.load(f)

# Sort ascending by original_air_date
episodes.sort(
    key=lambda ep: datetime.strptime(
        ep["original_air_date"].split(" +")[0], "%a, %d %b %Y %H:%M:%S"
    )
)

# Write Markdown
with open(md_file, "w") as out:
    out.write("Title|Release Date|Download|Clean|Segments|\n")
    out.write("---|:-:|:-:|:-:|-\n")

    for ep in episodes:
        number = ep.get("number")
        title = ep.get("title")
        url = ep.get("episode_url")
        download = ep.get("download")
        download_clean = ep.get("download_clean")
        air_date = datetime.strptime(
            ep["original_air_date"].split(" +")[0], "%a, %d %b %Y %H:%M:%S"
        ).date()
        acts = ep.get("acts", [])
        act_titles = "; ".join(act.get("title") for act in acts)

        clean_link = f"[dl]({download_clean})" if download_clean else "-"

        out.write(
            f"[{number}: {title}]({url})|{air_date}|[dl]({download})|{clean_link}|{act_titles}\n"
        )
