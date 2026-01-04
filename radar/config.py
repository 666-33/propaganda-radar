from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List
import yaml

@dataclass
class GlobalConfig:
    mode: str
    watch_threshold: int
    red_threshold: int
    full_text_scope: str
    timeout_sec: int
    user_agent: str
    max_feed_items_per_source: int
    keep_days: int
    max_items_per_section: int
    include_green_in_md: bool
    include_green_in_telegram: bool

@dataclass
class SourceConfig:
    id: str
    name: str
    url: str
    policy: str
    keywords: List[Dict[str, Any]]
    context_rules: List[Dict[str, Any]]

@dataclass
class AppConfig:
    global_cfg: GlobalConfig
    sources: List[SourceConfig]

def _must(d: Dict[str, Any], k: str, ctx: str) -> Any:
    if k not in d:
        raise ValueError(f"Missing required key '{k}' in {ctx}")
    return d[k]

def load_config(path: str) -> AppConfig:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    g = _must(data, "global", "root.global")
    thresholds = _must(g, "thresholds", "root.global.thresholds")
    req = _must(g, "request", "root.global.request")
    dedupe = _must(g, "dedupe", "root.global.dedupe")
    digest = _must(g, "digest", "root.global.digest")

    global_cfg = GlobalConfig(
        mode=str(_must(g, "mode", "root.global.mode")).strip(),
        watch_threshold=int(_must(thresholds, "watch", "root.global.thresholds.watch")),
        red_threshold=int(_must(thresholds, "red", "root.global.thresholds.red")),
        full_text_scope=str(_must(g, "full_text_scope", "root.global.full_text_scope")).strip(),
        timeout_sec=int(_must(req, "timeout_sec", "root.global.request.timeout_sec")),
        user_agent=str(_must(req, "user_agent", "root.global.request.user_agent")),
        max_feed_items_per_source=int(_must(req, "max_feed_items_per_source", "root.global.request.max_feed_items_per_source")),
        keep_days=int(_must(dedupe, "keep_days", "root.global.dedupe.keep_days")),
        max_items_per_section=int(_must(digest, "max_items_per_section", "root.global.digest.max_items_per_section")),
        include_green_in_md=bool(digest.get("include_green_in_md", True)),
        include_green_in_telegram=bool(digest.get("include_green_in_telegram", False)),
    )

    sources_raw = _must(data, "sources", "root.sources")
    sources: List[SourceConfig] = []
    for i, s in enumerate(sources_raw):
        ctx = f"root.sources[{i}]"
        sources.append(
            SourceConfig(
                id=str(_must(s, "id", f"{ctx}.id")).strip(),
                name=str(_must(s, "name", f"{ctx}.name")).strip(),
                url=str(_must(s, "url", f"{ctx}.url")).strip(),
                policy=str(_must(s, "policy", f"{ctx}.policy")).strip(),
                keywords=list(s.get("keywords", [])),
                context_rules=list(s.get("context_rules", [])),
            )
        )

    return AppConfig(global_cfg=global_cfg, sources=sources)
