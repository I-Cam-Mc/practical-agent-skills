#!/usr/bin/env python3
"""Run deterministic source-level checks on a generated clean-room deck."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
import json
from pathlib import Path


class DeckParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.slides = 0
        self.dots = 0
        self.images: list[str] = []
        self.external_dependencies: list[str] = []
        self.banned_tags: list[str] = []
        self.portable_deck_marker = False
        self.csp = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        if tag == "section" and "slide" in classes:
            self.slides += 1
        if tag == "button" and "dot" in classes:
            self.dots += 1
        if tag == "img":
            self.images.append(values.get("src") or "")
            if not values.get("alt"):
                self.external_dependencies.append("image without alternative text")
        if tag in {"iframe", "object", "embed", "form"}:
            self.banned_tags.append(tag)
        if values.get("src") and tag in {"script", "audio", "video", "source"}:
            self.external_dependencies.append(f"{tag}[src]={values['src']}")
        if tag == "link" and values.get("href"):
            self.external_dependencies.append(f"link[href]={values['href']}")
        if tag == "body" and values.get("data-portable-deck") == "v1":
            self.portable_deck_marker = True
        if tag == "meta" and (values.get("http-equiv") or "").lower() == "content-security-policy":
            self.csp = values.get("content") or ""


def validate(path: Path) -> list[str]:
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"cannot read deck: {exc}"]
    parser = DeckParser()
    parser.feed(source)
    failures: list[str] = []
    if not parser.portable_deck_marker:
        failures.append("missing portable deck marker")
    if parser.slides < 1:
        failures.append("no slides found")
    if parser.slides != parser.dots:
        failures.append(f"slide and navigation counts differ: {parser.slides} vs {parser.dots}")
    if parser.banned_tags:
        failures.append("banned embedded elements: " + ", ".join(parser.banned_tags))
    for image in parser.images:
        if not image.startswith("data:image/"):
            failures.append("image is not embedded as a data URI")
    failures.extend(parser.external_dependencies)
    csp_requirements = ("default-src 'none'", "connect-src 'none'", "object-src 'none'", "frame-src 'none'")
    for requirement in csp_requirements:
        if requirement not in parser.csp:
            failures.append(f"content security policy lacks {requirement}")
    if "prefers-reduced-motion" not in source:
        failures.append("reduced-motion CSS is missing")
    if "@media print" not in source:
        failures.append("print CSS is missing")
    for forbidden in ("gsap", "greensock", "stratumlabs", "file://"):
        if forbidden in source.lower():
            failures.append(f"forbidden dependency or source marker found: {forbidden}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("deck", type=Path)
    args = parser.parse_args()
    failures = validate(args.deck)
    print(json.dumps({"ok": not failures, "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
