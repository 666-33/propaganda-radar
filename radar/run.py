from __future__ import annotations

import argparse
import hashlib
import os
import traceback
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from radar.config import load_config
from radar.state import (
    load_state, save_state, is_seen, mark_seen, prune_seen,
    get_last_sent_date, set_last_sent_date
)
from radar.fetch import fetch_feed, fetch_html
from radar.extract import extract_text_from_html, lead_paragraphs
from radar.score import score_item, classify
from radar.render import render_daily_markdown
from radar.telegram import build_digest_message, send_telegram_message


def ensure_dirs() -> None:
    os.makedirs("out/daily", exist_ok=True)
    os.makedirs("out/logs", exist_ok=True)


def log_path() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"out/logs/run_{ts}.log"


class Logger:
    def __init__(self, path: str):
        self.path = path

    def _write(self, level: str, msg: str):
        line = f"[{datetime.now(timezone.utc).isoformat()}] {level}: {msg}\n"
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line)

    def info(self, msg: str): self._write("INFO", msg)
    def warn(self, msg: str): self._write("WARN", msg)
    def error(self, msg: str): self._write("ERROR", msg)


def stable_key(source_id: str, entry: Any) -> str:
    guid = entry.get("id") or ""
    link = entry.get("link") or ""
    title = entry.get("title") or ""
    base = f"{source_id}::{guid or link or title}".strip()
    return hashlib.sha1(base.encode("utf-8")).hexdigest()


def get_entry_published(entry: Any) -> str:
    try:
        if entry.get("published"):
            return str(entry.get("published"))
        if entry.get("updated"):
            return str(entry.get("updated"))
    except Exception:
        pass
    return ""


def compact_matches(matched_keywords, matched_rules) -> str:
    parts = []
    if matched_keywords:
        top = sorted(matched_keywords, key=lambda x: (-x[1], -x[2]))[:5]
        parts.append("KW: " + ", ".join([f"{t}*{w}({c})" for t, w, c in top]))
    if matched_rules:
        top2 = sorted(matched_rules, key=lambda x: -x[1])[:5]
        parts.append("CTX: " + ", ".join([f"{n}(+{w})" for n, w in top2]))
    return " | ".join(parts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="sources.yaml")
    parser.add_argument("--state", default="state.json")
    parser.add_argument("--date", default=None, help="YYYY-MM-DD (default: UTC today)")
    parser.add_argument("--send-telegram", default=None, help="true/false; overrides env SEND_TELEGRAM")
    args = parser.parse_args()

    ensure_dirs()
    lp = log_path()
    log = Logger(lp)
    log.info("Starting run")

    cfg = load_config(args.config)
    state = load_state(args.state)

    date_str = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    send_env = os.getenv("SEND_TELEGRAM", "false").strip().lower()
    if args.send_telegram is not None:
        send_env = str(args.send_telegram).strip().lower()
    send_telegram = send_env in ("1", "true", "yes", "y")

    new_items: List[Dict[str, Any]] = []

    # prune seen
    try:
        removed = prune_seen(state, cfg.global_cfg.keep_days)
        log.info(f"Pruned seen entries: {removed}")
    except Exception as e:
        log.error(f"Failed prune_seen: {e}")

    def try_fetch_and_extract(link: str) -> Optional[str]:
        if not link:
            return None
        try:
            html = fetch_html(link, cfg.global_cfg.timeout_sec, cfg.global_cfg.user_agent)
            return extract_text_from_html(html, link)
        except Exception as ex:
            log.warn(f"HTML extract failed: {ex}")
            return None

    for s in cfg.sources:
        log.info(f"Fetching feed: {s.id} {s.url}")
        try:
            feed = fetch_feed(s.url, cfg.global_cfg.timeout_sec, cfg.global_cfg.user_agent)
        except Exception as e:
            log.error(f"Feed fetch failed for {s.id}: {e}")
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
                published = get_entry_published(entry)

                # 1) RSS 기반 1차 스코어
                sr = score_item(
                    title=title,
                    summary=summary,
                    body="",
                    keywords=s.keywords,
                    context_rules=s.context_rules,
                    mode=cfg.global_cfg.mode,
                )
                label = classify(sr.score, cfg.global_cfg.watch_threshold, cfg.global_cfg.red_threshold)

                policy = (s.policy or "RSS_ONLY").strip().upper()
                policy_used = "RSS_ONLY"
                excerpt = summary[:1200] if summary else ""

                if policy == "RSS_ONLY":
                    policy_used = "RSS_ONLY"

                elif policy == "LEAD_3_PARAGRAPHS":
                    text = try_fetch_and_extract(link)
                    if text:
                        lead = lead_paragraphs(text, 3)
                        sr = score_item(title, summary, lead, s.keywords, s.context_rules, cfg.global_cfg.mode)
                        label = classify(sr.score, cfg.global_cfg.watch_threshold, cfg.global_cfg.red_threshold)
                        policy_used = "LEAD_3_PARAGRAPHS"
                        excerpt = lead if lead else excerpt
                    else:
                        policy_used = "RSS_ONLY"

                elif policy == "FULL_TEXT":
                    # 기본 안전장치: full_text_scope=RED면 RED인 경우에만 FULL_TEXT
                    text = try_fetch_and_extract(link)
                    if text:
                        lead = lead_paragraphs(text, 3)
                        sr2 = score_item(title, summary, lead, s.keywords, s.context_rules, cfg.global_cfg.mode)
                        label2 = classify(sr2.score, cfg.global_cfg.watch_threshold, cfg.global_cfg.red_threshold)

                        scope = (cfg.global_cfg.full_text_scope or "RED").strip().upper()
                        if scope == "ALL" or label2 == "RED":
                            policy_used = "FULL_TEXT"
                            sr = sr2
                            label = label2
                            excerpt = text[:2500]
                        else:
                            policy_used = "LEAD_3_PARAGRAPHS"
                            sr = sr2
                            label = label2
                            excerpt = lead if lead else (summary[:1200] if summary else "")
                    else:
                        policy_used = "RSS_ONLY"

                else:
                    policy_used = "RSS_ONLY"

                item = {
                    "date": date_str,
                    "source_id": s.id,
                    "source_name": s.name,
                    "title": title if title else "(no title)",
                    "link": link if link else "",
                    "published": published,
                    "score": sr.score,
                    "label": label,
                    "policy_used": policy_used,
                    "matches": compact_matches(sr.matched_keywords, sr.matched_rules),
                    "excerpt": (excerpt or "").strip(),
                }

                mark_seen(state, key, {
                    "date": date_str,
                    "source_id": s.id,
                    "title": item["title"][:200],
                    "link": item["link"][:500],
                    "label": item["label"],
                    "score": item["score"],
                })
                new_items.append(item)

            except Exception as e:
                log.error(f"Entry processing failed ({s.id}): {e}\n{traceback.format_exc()}")
                continue

    # 정렬
    order = {"RED": 0, "WATCH": 1, "GREEN": 2}
    new_items.sort(key=lambda x: (order.get(x["label"], 9), -int(x["score"])))

    # daily md 저장
    out_md = f"out/daily/daily_{date_str}.md"
    try:
        md = render_daily_markdown(date_str, new_items, include_green=cfg.global_cfg.include_green_in_md)
        with open(out_md, "w", encoding="utf-8") as f:
            f.write(md)
        log.info(f"Wrote {out_md}")
    except Exception as e:
        log.error(f"Failed to write daily md: {e}")

    # state 저장
    try:
        save_state(args.state, state)
        log.info("Saved state.json")
    except Exception as e:
        log.error(f"Failed save_state: {e}")

    # 텔레그램: “하루 1개 Digest” (SEND_TELEGRAM=true일 때만 시도)
    try:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        last_sent = get_last_sent_date(state)

        if send_telegram and bot_token and chat_id:
            if last_sent == date_str:
                log.info(f"Telegram already sent for {date_str}; skipping")
            else:
                if len(new_items) == 0:
                    log.info("No new items; telegram skipped")
                else:
                    msg = build_digest_message(
                        date_str=date_str,
                        items=new_items,
                        max_items_per_section=cfg.global_cfg.max_items_per_section,
                        include_green=cfg.global_cfg.include_green_in_telegram,
                    )
                    send_telegram_message(bot_token, chat_id, msg, timeout_sec=cfg.global_cfg.timeout_sec)
                    set_last_sent_date(state, date_str)
                    save_state(args.state, state)
                    log.info("Telegram sent and state updated")
        else:
            log.info(f"Telegram not sent (SEND_TELEGRAM={send_telegram}, token/chat present={bool(bot_token and chat_id)})")
    except Exception as e:
        log.error(f"Telegram send failed: {e}")

    print(f"OK: items={len(new_items)} -> {out_md} (log: {lp})")


if __name__ == "__main__":
    main()
