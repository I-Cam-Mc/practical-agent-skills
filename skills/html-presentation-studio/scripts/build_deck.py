#!/usr/bin/env python3
"""Build a dependency-free, self-contained HTML slide deck from JSON."""

from __future__ import annotations

import argparse
import base64
from html import escape
import json
from pathlib import Path
from typing import Any


ALLOWED_TYPES = {"hero", "bullets", "two-column", "quote", "metrics"}
ALLOWED_IMAGES = {".gif", ".jpeg", ".jpg", ".png", ".webp"}
MAX_IMAGE_BYTES = 15 * 1024 * 1024
IMAGE_MIME_TYPES = {
    ".gif": "image/gif",
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


class SpecError(ValueError):
    """The deck specification is invalid or unsafe."""


def valid_image_bytes(suffix: str, payload: bytes) -> bool:
    """Perform a bounded structural signature check for supported raster files."""
    if suffix == ".png":
        return (
            len(payload) >= 24
            and payload.startswith(b"\x89PNG\r\n\x1a\n")
            and payload[12:16] == b"IHDR"
            and int.from_bytes(payload[16:20], "big") > 0
            and int.from_bytes(payload[20:24], "big") > 0
        )
    if suffix in {".jpg", ".jpeg"}:
        return (
            len(payload) >= 4
            and payload.startswith(b"\xff\xd8\xff")
            and payload.endswith(b"\xff\xd9")
        )
    if suffix == ".gif":
        return (
            len(payload) >= 10
            and payload[:6] in {b"GIF87a", b"GIF89a"}
            and int.from_bytes(payload[6:8], "little") > 0
            and int.from_bytes(payload[8:10], "little") > 0
        )
    if suffix == ".webp":
        return (
            len(payload) >= 16
            and payload.startswith(b"RIFF")
            and payload[8:12] == b"WEBP"
            and int.from_bytes(payload[4:8], "little") == len(payload) - 8
        )
    return False


def text(value: Any, *, field: str, required: bool = False) -> str:
    if value is None and not required:
        return ""
    if not isinstance(value, str) or (required and not value.strip()):
        raise SpecError(f"{field} must be {'a non-empty ' if required else 'a '}string")
    return value.strip()


def string_list(value: Any, *, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise SpecError(f"{field} must be an array of strings")
    return [item.strip() for item in value if item.strip()]


def embed_image(value: Any, alt_value: Any, spec_dir: Path, field: str) -> str:
    if value is None:
        return ""
    path_value = text(value, field=field, required=True)
    candidate = Path(path_value)
    if candidate.is_absolute() or "://" in path_value or path_value.startswith("data:"):
        raise SpecError(f"{field} must be a relative local image path")
    root = spec_dir.resolve()
    source = (root / candidate).resolve()
    try:
        source.relative_to(root)
    except ValueError as exc:
        raise SpecError(f"{field} escapes the spec directory") from exc
    suffix = source.suffix.lower()
    if suffix not in ALLOWED_IMAGES:
        raise SpecError(f"{field} must use a supported raster image type")
    if not source.is_file():
        raise SpecError(f"{field} does not exist: {path_value}")
    if source.stat().st_size > MAX_IMAGE_BYTES:
        raise SpecError(f"{field} exceeds the 15 MiB limit")
    payload = source.read_bytes()
    if not valid_image_bytes(suffix, payload):
        raise SpecError(f"{field} bytes do not match its supported image type")
    mime = IMAGE_MIME_TYPES[suffix]
    encoded = base64.b64encode(payload).decode("ascii")
    alt = escape(text(alt_value, field=f"{field}_alt", required=True), quote=True)
    return f'<figure class="media"><img src="data:{mime};base64,{encoded}" alt="{alt}"></figure>'


def heading_block(slide: dict[str, Any], index: int) -> str:
    eyebrow = text(slide.get("eyebrow"), field=f"slides[{index}].eyebrow")
    title = text(slide.get("title"), field=f"slides[{index}].title", required=True)
    body = text(slide.get("body"), field=f"slides[{index}].body")
    parts = []
    if eyebrow:
        parts.append(f'<p class="eyebrow">{escape(eyebrow)}</p>')
    parts.append(f"<h2>{escape(title)}</h2>")
    if body:
        parts.append(f'<p class="lede">{escape(body)}</p>')
    return "\n".join(parts)


def bullet_markup(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>"


def render_slide(slide: Any, index: int, spec_dir: Path) -> str:
    if not isinstance(slide, dict):
        raise SpecError(f"slides[{index}] must be an object")
    slide_type = text(slide.get("type"), field=f"slides[{index}].type", required=True)
    if slide_type not in ALLOWED_TYPES:
        raise SpecError(f"slides[{index}].type is unsupported: {slide_type}")

    image = embed_image(
        slide.get("image"),
        slide.get("image_alt"),
        spec_dir,
        f"slides[{index}].image",
    )
    source = text(slide.get("source"), field=f"slides[{index}].source")

    if slide_type == "hero":
        eyebrow = text(slide.get("eyebrow"), field=f"slides[{index}].eyebrow")
        title = text(slide.get("title"), field=f"slides[{index}].title", required=True)
        body = text(slide.get("body"), field=f"slides[{index}].body")
        content = (
            (f'<p class="eyebrow">{escape(eyebrow)}</p>' if eyebrow else "")
            + f"<h1>{escape(title)}</h1>"
            + (f'<p class="lede">{escape(body)}</p>' if body else "")
            + image
        )
    elif slide_type == "bullets":
        items = string_list(slide.get("items"), field=f"slides[{index}].items")
        if not items:
            raise SpecError(f"slides[{index}].items must not be empty")
        content = heading_block(slide, index) + bullet_markup(items) + image
    elif slide_type == "two-column":
        columns = []
        for name in ("left", "right"):
            column = slide.get(name)
            if not isinstance(column, dict):
                raise SpecError(f"slides[{index}].{name} must be an object")
            heading = text(column.get("heading"), field=f"slides[{index}].{name}.heading", required=True)
            body = text(column.get("body"), field=f"slides[{index}].{name}.body")
            items = string_list(column.get("items"), field=f"slides[{index}].{name}.items")
            columns.append(
                '<article class="column">'
                + f"<h3>{escape(heading)}</h3>"
                + (f"<p>{escape(body)}</p>" if body else "")
                + (bullet_markup(items) if items else "")
                + "</article>"
            )
        content = heading_block(slide, index) + '<div class="columns">' + "".join(columns) + "</div>" + image
    elif slide_type == "quote":
        quote = text(slide.get("quote"), field=f"slides[{index}].quote", required=True)
        attribution = text(slide.get("attribution"), field=f"slides[{index}].attribution")
        content = heading_block(slide, index) + f"<blockquote>{escape(quote)}</blockquote>"
        if attribution:
            content += f'<p class="attribution">{escape(attribution)}</p>'
        content += image
    else:
        metrics = slide.get("metrics")
        if not isinstance(metrics, list) or not metrics:
            raise SpecError(f"slides[{index}].metrics must be a non-empty array")
        rendered_metrics = []
        for metric_index, metric in enumerate(metrics):
            if not isinstance(metric, dict):
                raise SpecError(f"slides[{index}].metrics[{metric_index}] must be an object")
            value = text(metric.get("value"), field="metric.value", required=True)
            label = text(metric.get("label"), field="metric.label", required=True)
            rendered_metrics.append(
                f'<article class="metric"><strong>{escape(value)}</strong><span>{escape(label)}</span></article>'
            )
        content = heading_block(slide, index) + '<div class="metrics">' + "".join(rendered_metrics) + "</div>" + image

    if source:
        content += f'<p class="source">Source: {escape(source)}</p>'
    return (
        f'<section class="slide slide--{slide_type}" id="slide-{index + 1}" tabindex="-1">'
        f'<div class="slide-inner">{content}</div></section>'
    )


CSS = r"""
:root { color-scheme: light dark; --ink:#17212b; --paper:#f5f1e8; --accent:#d65a3a; --muted:#66717c; --rule:#bdc6cd; }
* { box-sizing:border-box; }
html { scroll-behavior:smooth; background:var(--ink); }
body { margin:0; font-family:Inter,ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; color:var(--ink); background:var(--ink); }
.deck { scroll-snap-type:y mandatory; }
.slide { min-height:100svh; scroll-snap-align:start; display:grid; place-items:center; padding:clamp(3rem,7vw,7rem); background:var(--paper); overflow:hidden; }
.slide:nth-child(even) { color:var(--paper); background:var(--ink); }
.slide-inner { width:min(1120px,100%); min-width:0; }
.eyebrow,.source { font:600 .78rem/1.4 ui-monospace,SFMono-Regular,Menlo,monospace; letter-spacing:.09em; text-transform:uppercase; }
.eyebrow { color:var(--accent); }
h1,h2 { max-width:16ch; margin:.2em 0; font-weight:760; letter-spacing:-.045em; text-wrap:balance; }
h1 { font-size:clamp(3rem,8vw,7.5rem); line-height:.92; }
h2 { font-size:clamp(2.2rem,5.4vw,5rem); line-height:1; }
h3 { font-size:clamp(1.2rem,2vw,1.65rem); }
.lede,li,p { font-size:clamp(1rem,1.7vw,1.45rem); line-height:1.45; }
.lede { max-width:48rem; color:var(--muted); }
.slide:nth-child(even) .lede,.slide:nth-child(even) .source { color:#b8c1c8; }
ul { display:grid; gap:.75rem; max-width:55rem; padding-left:1.25em; }
.columns { display:grid; grid-template-columns:1fr 1fr; gap:clamp(1rem,4vw,4rem); margin-top:2rem; }
.column { border-top:2px solid var(--accent); padding-top:1rem; min-width:0; }
blockquote { max-width:22ch; margin:1em 0 .35em; font-size:clamp(2rem,5vw,4.5rem); line-height:1.05; font-weight:680; }
.attribution { color:var(--muted); }
.metrics { display:grid; grid-template-columns:repeat(auto-fit,minmax(10rem,1fr)); gap:1rem; margin-top:2rem; }
.metric { border-top:2px solid var(--accent); padding-top:1rem; }
.metric strong,.metric span { display:block; }
.metric strong { font-size:clamp(2.4rem,6vw,5.5rem); line-height:1; }
.metric span { margin-top:.55rem; font-size:1rem; }
.media { margin:2rem 0 0; max-width:min(54rem,100%); }
.media img { display:block; max-width:100%; max-height:42svh; object-fit:contain; }
.source { margin-top:2rem; color:var(--muted); text-transform:none; letter-spacing:.02em; }
.counter { position:fixed; z-index:10; right:1rem; bottom:1rem; padding:.45rem .65rem; color:var(--paper); background:rgba(23,33,43,.9); font:600 .78rem/1 ui-monospace,SFMono-Regular,Menlo,monospace; }
.rail { position:fixed; z-index:10; left:1rem; top:50%; transform:translateY(-50%); display:grid; gap:.55rem; }
.dot { width:.75rem; height:.75rem; padding:0; border:1px solid rgba(245,241,232,.8); border-radius:50%; background:rgba(23,33,43,.6); cursor:pointer; }
.dot[aria-current="true"] { background:var(--accent); transform:scale(1.25); }
.dot:focus-visible { outline:3px solid #fff; outline-offset:3px; }
@media (max-width:700px) { .slide { padding:4.5rem 2rem 5rem; } .columns { grid-template-columns:1fr; gap:1rem; } .rail { left:.5rem; } h1 { font-size:clamp(2.7rem,15vw,5rem); } }
@media (prefers-reduced-motion:reduce) { html { scroll-behavior:auto; } *,*::before,*::after { animation-duration:.01ms!important; transition-duration:.01ms!important; } }
@media print { .rail,.counter { display:none!important; } .slide { min-height:100vh; break-after:page; page-break-after:always; } }
"""


JAVASCRIPT = r"""
(() => {
  const slides = [...document.querySelectorAll('.slide')];
  const dots = [...document.querySelectorAll('.dot')];
  const current = document.getElementById('current');
  let index = 0;
  let queued = false;
  const select = (next, scroll) => {
    index = Math.max(0, Math.min(slides.length - 1, next));
    current.textContent = String(index + 1).padStart(2, '0');
    dots.forEach((dot, i) => dot.setAttribute('aria-current', String(i === index)));
    if (scroll) slides[index].scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
  };
  const updateFromScroll = () => {
    queued = false;
    const centre = innerHeight / 2;
    let nearest = 0;
    let distance = Infinity;
    slides.forEach((slide, i) => {
      const rect = slide.getBoundingClientRect();
      const candidate = Math.abs(rect.top + rect.height / 2 - centre);
      if (candidate < distance) { distance = candidate; nearest = i; }
    });
    select(nearest, false);
  };
  addEventListener('scroll', () => { if (!queued) { queued = true; requestAnimationFrame(updateFromScroll); } }, {passive:true});
  addEventListener('resize', updateFromScroll);
  addEventListener('keydown', event => {
    if (['ArrowRight','ArrowDown','PageDown',' '].includes(event.key)) { event.preventDefault(); select(index + 1, true); }
    if (['ArrowLeft','ArrowUp','PageUp'].includes(event.key)) { event.preventDefault(); select(index - 1, true); }
    if (event.key === 'Home') { event.preventDefault(); select(0, true); }
    if (event.key === 'End') { event.preventDefault(); select(slides.length - 1, true); }
  });
  dots.forEach((dot, i) => dot.addEventListener('click', () => select(i, true)));
  select(0, false);
})();
"""


def build_deck(spec_path: Path, output_path: Path) -> Path:
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SpecError(f"cannot read spec: {exc}") from exc
    if not isinstance(spec, dict):
        raise SpecError("spec root must be an object")
    title = text(spec.get("title"), field="title", required=True)
    subtitle = text(spec.get("subtitle"), field="subtitle")
    author = text(spec.get("author"), field="author")
    slides = spec.get("slides")
    if not isinstance(slides, list) or not 1 <= len(slides) <= 50:
        raise SpecError("slides must contain between 1 and 50 objects")

    rendered = "\n".join(render_slide(slide, index, spec_path.parent) for index, slide in enumerate(slides))
    dots = "".join(
        f'<button class="dot" type="button" aria-label="Go to slide {index + 1}" aria-current="false"></button>'
        for index in range(len(slides))
    )
    metadata = escape(json.dumps({"title": title, "author": author, "slides": len(slides)}, sort_keys=True))
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; img-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'; font-src data:; media-src data:; object-src 'none'; frame-src 'none'; base-uri 'none'; form-action 'none'">
  <meta name="description" content="{escape(subtitle, quote=True)}">
  <title>{escape(title)}</title>
  <style>{CSS}</style>
</head>
<body data-portable-deck="v1" data-deck-metadata="{metadata}">
  <nav class="rail" aria-label="Slide navigation">{dots}</nav>
  <div class="counter" aria-live="polite"><span id="current">01</span> / {len(slides):02d}</div>
  <main class="deck">{rendered}</main>
  <script>{JAVASCRIPT}</script>
</body>
</html>
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(document, encoding="utf-8")
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        output = build_deck(args.spec, args.output)
    except SpecError as exc:
        parser.exit(2, f"deck build failed: {exc}\n")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
