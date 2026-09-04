# html-presentation-studio

A Codex skill and newly written standard-library builder for accessible,
self-contained HTML slide decks. No source code or assets from the audited local
implementation are included.

Generated decks contain their CSS, JavaScript and approved local raster images
inside one HTML file. They use native browser behaviour and do not bundle GSAP,
web fonts, analytics, third-party templates or exemplar content.

## Build the example

```bash
python3 scripts/build_deck.py assets/example-spec.json /tmp/html-deck/index.html
python3 scripts/validate_deck.py /tmp/html-deck/index.html
```

The source validator catches structural and dependency errors. A human still
needs to inspect every generated slide in a real browser at the intended desktop
and mobile sizes.

If Playwright is already provisioned, the optional browser smoke test checks the
example at desktop and mobile sizes and writes screenshots plus a JSON report:

```bash
node tests/browser_smoke.cjs /tmp/html-deck/index.html /tmp/html-deck/browser-report
```

## Install

Copy this folder into your Codex skills directory and restart Codex.

## Validate the package

```bash
python3 -m unittest discover -s tests -v
python3 /path/to/skill-creator/scripts/quick_validate.py .
```

## Licence

MIT. Generated deck content and supplied media retain their own rights and are
not relicensed by this package.
