from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).parents[1]


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BUILD = load("build_deck", ROOT / "scripts" / "build_deck.py")
VALIDATE = load("validate_deck", ROOT / "scripts" / "validate_deck.py")


class DeckTests(unittest.TestCase):
    def test_builds_self_contained_deck(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "pixel.png"
            image.write_bytes(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="))
            spec = {
                "title": "Example",
                "slides": [
                    {"type": "hero", "title": "One idea", "image": "pixel.png", "image_alt": "One pixel"},
                    {"type": "bullets", "title": "Evidence", "items": ["First", "Second"]},
                ],
            }
            spec_path = root / "spec.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            output = BUILD.build_deck(spec_path, root / "out" / "index.html")
            self.assertEqual(VALIDATE.validate(output), [])
            source = output.read_text(encoding="utf-8")
            self.assertIn("data:image/png;base64,", source)

    def test_rejects_remote_image(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = {
                "title": "Example",
                "slides": [{"type": "hero", "title": "No remote files", "image": "https://example.com/a.png", "image_alt": "Remote"}],
            }
            spec_path = root / "spec.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            with self.assertRaises(BUILD.SpecError):
                BUILD.build_deck(spec_path, root / "index.html")

    def test_rejects_image_path_escape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            spec = {
                "title": "Example",
                "slides": [{"type": "hero", "title": "Contained", "image": "../outside.png", "image_alt": "Outside"}],
            }
            spec_path = root / "spec.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            with self.assertRaises(BUILD.SpecError):
                BUILD.build_deck(spec_path, root / "index.html")

    def test_rejects_text_renamed_as_png(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "not-an-image.png").write_text("plain text", encoding="utf-8")
            spec = {
                "title": "Example",
                "slides": [
                    {
                        "type": "hero",
                        "title": "Validate bytes",
                        "image": "not-an-image.png",
                        "image_alt": "Invalid image",
                    }
                ],
            }
            spec_path = root / "spec.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            with self.assertRaises(BUILD.SpecError):
                BUILD.build_deck(spec_path, root / "index.html")


if __name__ == "__main__":
    unittest.main()
