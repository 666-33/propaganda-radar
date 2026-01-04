from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple

@dataclass
class ScoreResult:
    score: int
    matched_keywords: List[Tuple[str, int, int]]
    matched_rules: List[Tuple[str, int]]

def _count_occurrences(text: str, term: str) -> int:
    if not text or not term:
        return 0
    return text.lower().count(term.lower())

def score_item(title: str, summary: str, keywords: List[Dict[str, Any]], context_rules: List[Dict[str, Any]], mode: str) -> ScoreResult:
    title = title or ""
    summary = summary or ""
    blob = f"{title}\n{summary}"

    aggressive = (mode or "").lower() == "aggressive"
    total = 0
    mk = []
    mr = []

    for kw in (keywords or []):
        term = str(kw.get("term", "")).strip()
        if not term:
            continue
        w = int(kw.get("weight", 1))
        c_title = _count_occurrences(title, term)
        c_sum = _count_occurrences(summary, term)
        c = c_title + c_sum
        if c <= 0:
            continue

        if aggressive:
            part = (c_title * w * 3) + (c_sum * w)
            if c_title > 0:
                part += 2
        else:
            part = c * w

        part = min(part, w * 12 + (3 if aggressive else 0))
        total += part
        mk.append((term, w, c))

    for rule in (context_rules or []):
        name = str(rule.get("name", "rule")).strip()
        patterns = rule.get("patterns", []) or []
        w = int(rule.get("weight", 1))
        match_mode = str(rule.get("match", "any")).lower()

        hits = 0
        for p in patterns:
            p = str(p).strip()
            if p and (p.lower() in blob.lower()):
                hits += 1

        ok = (hits > 0) if match_mode == "any" else (hits == len(patterns) and len(patterns) > 0)
        if ok:
            add = w * (2 if aggressive else 1)
            total += add
            mr.append((name, add))

    return ScoreResult(score=int(total), matched_keywords=mk, matched_rules=mr)

def classify(score: int, watch_threshold: int, red_threshold: int) -> str:
    if score >= red_threshold:
        return "RED"
    if score >= watch_threshold:
        return "WATCH"
    return "GREEN"
