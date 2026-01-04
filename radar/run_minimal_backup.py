from __future__ import annotations
import hashlib
import os
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List

from radar.config import load_config
from radar.state import load_state, save_state, is_seen, mark_seen, prune_seen
from radar.fetch import fetch_feed
from radar.score import score_item, classify
from radar.render import render_daily_markdown

def ensure_dirs() -> None:
    os.makedirs("out/daily", exist_ok=True)
    os.makedirs("out/logs", exist_ok=True)

def stable_key(source_id: str, entry: Any) -> str:
    guid = entry.get("id") or ""
    link = entry.get("link") or ""
    title = entry.get("title") or ""
    base = f"{source_id}::{guid or link or title}".strip()
    return hashlib.sha1(base.encode("utf-8")).hexdigest()

def main():
    ensure_dirs()
    cfg = load_config("sources.yaml")
    state = load_state("state.json")
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    try:
        prune_seen(state, cfg.global_cfg.keep_days)
    except Exception:
        pass

    new_items: List[Dict[str, Any]] = []

    for s in cfg.sources:
        try:
            feed = fetch_feed(s.url, cfg.global_cfg.timeout_sec, cfg.global_cfg.user_agent)
        except Exception as e:
            print(f"[ERROR] feed fetch failed: {s.id} {e}")
            continue

        entries = feed.entries[: cfg.global_cfg.max_feed_items_per_source]
        for entry in entries:
            try:
                key = stable_key(s.id, entry)
                if is_seen(state, key):
                    continue

                title = (entry.get("title") or "").strip()
                link = (entry.get("link") or "").strip()
                summary = (entry.get("summary") or entry.get("description") or "").strip()

                sr = score_item(
                    title=title,
                    summary=summary,
                    keywords=s.keywords,
                    context_rules=s.context_rules,
                    mode=cfg.global_cfg.mode,
                )
                label = classify(sr.score, cfg.global_cfg.watch_threshold, cfg.global_cfg.red_threshold)

                item = {
                    "date": date_str,
                    "source_id": s.id,
                    "source_name": s.name,
                    "title": title if title else "(no title)",
                    "link": link if link else "",
                    "score": sr.score,
                    "label": label,
                }

                mark_seen(state, key, {"date": date_str, "source_id": s.id, "title": item["title"][:200]})
                new_items.append(item)

            except Exception:
                print(f"[ERROR] entry processing failed: {s.id}\n{traceback.format_exc()}")
                continue

    order = {"RED": 0, "WATCH": 1, "GREEN": 2}
    new_items.sort(key=lambda x: (order.get(x["label"], 9), -int(x["score"])))

    out_md = f"out/daily/daily_{date_str}.md"
    md = render_daily_markdown(date_str, new_items)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(md)

    save_state("state.json", state)
    print(f"OK: items={len(new_items)} -> {out_md}")

if __name__ == "__main__":
    main()
