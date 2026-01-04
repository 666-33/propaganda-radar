from __future__ import annotations
import requests
from typing import Dict, List

def build_digest_message(date_str: str, items: List[Dict], max_items_per_section: int, include_green: bool) -> str:
    red = [x for x in items if x["label"] == "RED"]
    watch = [x for x in items if x["label"] == "WATCH"]
    green = [x for x in items if x["label"] == "GREEN"]

    lines = []
    lines.append(f"🛰️ Propaganda Radar — {date_str}")
    lines.append(f"NEW: {len(items)} | RED {len(red)} | WATCH {len(watch)} | GREEN {len(green)}")
    lines.append("")

    def add_section(tag: str, xs: List[Dict]):
        if not xs:
            return
        lines.append(tag)
        for i, it in enumerate(xs[:max_items_per_section], 1):
            title = (it.get("title") or "").replace("\n", " ").strip()
            link = it.get("link") or ""
            lines.append(f"{i}) {title} (score {it.get('score')})")
            if link:
                lines.append(f"   {link}")
        if len(xs) > max_items_per_section:
            lines.append(f"… and {len(xs) - max_items_per_section} more")
        lines.append("")

    add_section("🔴 RED", red)
    add_section("🟠 WATCH", watch)
    if include_green:
        add_section("🟢 GREEN", green)

    lines.append("—")
    lines.append("Repo의 out/daily/ 파일에서 전체 내용 확인")
    msg = "\n".join(lines)
    if len(msg) > 3800:
        msg = msg[:3800] + "\n…(truncated)"
    return msg

def send_telegram_message(bot_token: str, chat_id: str, text: str, timeout_sec: int = 20) -> None:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "disable_web_page_preview": True}
    r = requests.post(url, json=payload, timeout=timeout_sec)
    r.raise_for_status()
