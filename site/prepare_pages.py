"""Rewrite the built site so it opens under a GitHub Pages project path.

Local preview stays at the site root. Run this only in the publish workflow.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent / "dist"
BASE = "/partiya-yug"
OLD_ORIGIN = "https://partiya-yug-rostov.nbnandreu.chatgpt.site"
NEW_ORIGIN = "https://nbnandreu-svg.github.io/partiya-yug"
SUFFIXES = {".html", ".css", ".js", ".xml", ".txt", ".json"}


def rewrite(text: str) -> str:
    text = text.replace(OLD_ORIGIN, NEW_ORIGIN)
    text = re.sub(
        rf'(href|src|action)=(["\'])/(?!{BASE.strip("/")}/)',
        rf"\1=\2{BASE}/",
        text,
    )
    text = re.sub(
        rf'url\((["\']?)/(?!{BASE.strip("/")}/)',
        rf"url(\1{BASE}/",
        text,
    )
    return text


def main() -> None:
    changed = 0
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in SUFFIXES:
            continue
        original = path.read_text(encoding="utf-8")
        updated = rewrite(original)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed += 1
    (ROOT / ".nojekyll").write_text("", encoding="utf-8")
    print(f"updated {changed} files for {NEW_ORIGIN}")


if __name__ == "__main__":
    main()
