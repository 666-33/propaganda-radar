from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

def load_state(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"version": 1, "seen": {}, "telegram": {"last_sent_date": None}}
    except Exception:
        return {"version": 1, "seen": {}, "telegram": {"last_sent_date": None}}

def save_state(path: str, state: Dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def is_seen(state: Dict[str, Any], key: str) -> bool:
    return key in (state.get("seen") or {})

def mark_seen(state: Dict[str, Any], key: str, meta: Dict[str, Any]) -> None:
    seen = state.setdefault("seen", {})
    now = datetime.now(timezone.utc).isoformat()
    if key not in seen:
        seen[key] = {"first_seen": now}
    seen[key].update({"last_seen": now, **meta})

def prune_seen(state: Dict[str, Any], keep_days: int) -> int:
    seen = state.get("seen") or {}
    if not isinstance(seen, dict):
        state["seen"] = {}
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)
    to_del = []
    for k, v in seen.items():
        try:
            last = v.get("last_seen")
            if not last:
                continue
            dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
            if dt < cutoff:
                to_del.append(k)
        except Exception:
            continue
    for k in to_del:
        del seen[k]
    return len(to_del)

def get_last_sent_date(state: Dict[str, Any]) -> Optional[str]:
    try:
        return state.get("telegram", {}).get("last_sent_date")
    except Exception:
        return None

def set_last_sent_date(state: Dict[str, Any], date_str: str) -> None:
    state.setdefault("telegram", {})
    state["telegram"]["last_sent_date"] = date_str
