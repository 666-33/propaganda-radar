from __future__ import annotations
from datetime import datetime
from typing import Dict, List

def render_daily_markdown(date_str: str, items: List[Dict]) -> str:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    red = [x for x in items if x["label"] == "RED"]
    watch = [x for x in items if x["label"] == "WATCH"]
    green = [x for x in items if x["label"] == "GREEN"]

    def section(title: str, xs: List[Dict]) -> str:
        lines = [f"## {title} ({len(xs)})", ""]
        for i, it in enumerate(xs, 1):
            lines.append(f"### {i}. [{it['title']}]({it['link']})")
            lines.append(f"- Source: **{it['source_name']}** (`{it['source_id']}`)")
            lines.append(f"- Score: **{it['score']}** | Label: **{it['label']}**")
            lines.append("")
        lines.append("")
        return "\n".join(lines)

    out = []
    out.append(f"# Propaganda Radar Daily — {date_str}")
    out.append("")
    out.append(f"- Generated: {now}")
    out.append(f"- New Items: {len(items)} | RED: {len(red)} | WATCH: {len(watch)} | GREEN: {len(green)}")
    out.append("")
    out.append(section("🔴 RED", red))
    out.append(section("🟠 WATCH", watch))
    out.append(section("🟢 GREEN", green))
    return "\n".join(out)
