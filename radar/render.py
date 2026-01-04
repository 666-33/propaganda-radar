from __future__ import annotations
from datetime import datetime
from typing import Dict, List

def render_daily_markdown(date_str: str, items: List[Dict], include_green: bool) -> str:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    red = [x for x in items if x["label"] == "RED"]
    watch = [x for x in items if x["label"] == "WATCH"]
    green = [x for x in items if x["label"] == "GREEN"]

    def section(title: str, xs: List[Dict]) -> str:
        lines = [f"## {title} ({len(xs)})", ""]
        for i, it in enumerate(xs, 1):
            lines.append(f"### {i}. [{it['title']}]({it['link']})")
            lines.append(f"- Source: **{it['source_name']}** (`{it['source_id']}`)")
            if it.get("published"):
                lines.append(f"- Published: {it['published']}")
            lines.append(f"- Policy Used: `{it.get('policy_used','RSS_ONLY')}` | Score: **{it['score']}** | Label: **{it['label']}**")
            if it.get("matches"):
                lines.append(f"- Matches: {it['matches']}")
            lines.append("")
            if it.get("excerpt"):
                lines.append("**Excerpt**")
                lines.append("")
                lines.append(it["excerpt"])
                lines.append("")
            lines.append("---")
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
    if include_green:
        out.append(section("🟢 GREEN", green))
    return "\n".join(out)
