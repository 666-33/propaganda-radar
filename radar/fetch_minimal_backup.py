from __future__ import annotations
import requests
import feedparser

def fetch_feed(url: str, timeout_sec: int, user_agent: str) -> feedparser.FeedParserDict:
    headers = {"User-Agent": user_agent, "Accept": "application/rss+xml, application/xml;q=0.9, */*;q=0.8"}
    r = requests.get(url, headers=headers, timeout=timeout_sec)
    r.raise_for_status()
    return feedparser.parse(r.content)
