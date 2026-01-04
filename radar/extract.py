from __future__ import annotations
from typing import Optional, List
import trafilatura

def extract_text_from_html(html: str, url: str) -> Optional[str]:
    try:
        text = trafilatura.extract(
            html,
            url=url,
            include_comments=False,
            include_tables=False,
            include_images=False,
            favor_precision=True,
        )
        if not text:
            return None
        cleaned = "\n".join([line.strip() for line in text.splitlines() if line.strip()])
        return cleaned if cleaned.strip() else None
    except Exception:
        return None

def lead_paragraphs(text: str, n: int = 3) -> str:
    if not text:
        return ""
    chunks: List[str] = []
    buf: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            if buf:
                chunks.append(" ".join(buf).strip())
                buf = []
            continue
        buf.append(line)
    if buf:
        chunks.append(" ".join(buf).strip())
    chunks = [c for c in chunks if c]
    return "\n\n".join(chunks[:n])
