"""Render the standalone HTML diagram to the PNG used by GitHub README."""

import argparse
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "docs" / "architecture.html"
OUTPUT = ROOT / "docs" / "assets" / "architecture.png"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")


def main() -> None:
    parser = argparse.ArgumentParser(description="Render the architecture HTML with local Chrome")
    parser.add_argument("--width", type=int, default=1480)
    parser.add_argument("--height", type=int, default=1240)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    target = args.output.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="architecture-render-") as profile:
        result = subprocess.run([
            str(CHROME), "--headless=new", "--disable-gpu", "--hide-scrollbars",
            f"--user-data-dir={profile}", f"--window-size={args.width},{args.height}",
            f"--screenshot={target}", HTML.resolve().as_uri(),
        ], capture_output=True, text=True, timeout=45)
    if result.returncode != 0 or not target.is_file():
        raise RuntimeError(f"Chrome render failed (exit={result.returncode})")
    print(target, target.stat().st_size)


if __name__ == "__main__":
    main()
