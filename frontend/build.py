#!/usr/bin/env python3
"""Native Python bundler for Multizone Thermostat frontend cards.

Assembles modular component source files from `frontend/src/` into the
standalone production bundles in `custom_components/multizone_thermostat/www/`.

Usage:
    python frontend/build.py           # Build production bundles
    python frontend/build.py --check   # Check if bundles are up-to-date (CI mode)
    python frontend/build.py --watch   # Watch for changes and rebuild automatically
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

ROOT_DIR = Path(__file__).resolve().parent.parent
FRONTEND_SRC_DIR = ROOT_DIR / "frontend" / "src"
WWW_DIR = ROOT_DIR / "custom_components" / "multizone_thermostat" / "www"

OUTPUT_CARD = WWW_DIR / "multizone-thermostat-card.js"
OUTPUT_CARD_V24 = WWW_DIR / "multizone-thermostat-card-v24.js"

SRC_FILES = [
    "00_header.js",
    "01_translations.js",
    "02_helpers.js",
    "components/button_card.js",
    "components/dial_card.js",
    "components/status_card.js",
    "components/preset_card.js",
    "components/summary_cards.js",
    "components/nav_cards.js",
    "components/plant_card.js",
    "components/zone_energy_card.js",
    "components/scheduler_card.js",
    "components/style_switcher.js",
    "strategies/dashboard_strategy.js",
]


def assemble_bundle() -> str:
    """Read all source modules in order and concatenate them."""
    chunks: list[str] = []
    for rel_path in SRC_FILES:
        src_file = FRONTEND_SRC_DIR / rel_path
        if not src_file.exists():
            print(f"Error: Required source file missing: {src_file}", file=sys.stderr)
            sys.exit(1)
        content = src_file.read_text(encoding="utf-8")
        chunks.append(content)
    return "".join(chunks)


def build(check_only: bool = False) -> bool:
    """Build or verify the production bundle."""
    bundle = assemble_bundle()
    WWW_DIR.mkdir(parents=True, exist_ok=True)

    if check_only:
        if not OUTPUT_CARD.exists():
            print("Check failed: Output card does not exist.", file=sys.stderr)
            return False
        current_content = OUTPUT_CARD.read_text(encoding="utf-8")
        if current_content != bundle:
            print("Check failed: Production bundle is out-of-date! Run 'python frontend/build.py'.", file=sys.stderr)
            return False
        print("Check passed: Production bundle is up-to-date.")
        return True

    OUTPUT_CARD.write_text(bundle, encoding="utf-8")
    OUTPUT_CARD_V24.write_text(bundle, encoding="utf-8")

    lines_count = len(bundle.splitlines())
    size_kb = round(len(bundle.encode("utf-8")) / 1024, 1)

    print(f"Bundled {len(SRC_FILES)} files -> {OUTPUT_CARD.name} & {OUTPUT_CARD_V24.name}")
    print(f"Total lines: {lines_count} | Size: {size_kb} KB")
    return True


def watch() -> None:
    """Watch src files and trigger rebuild on change."""
    print(f"Watching {FRONTEND_SRC_DIR} for changes (Ctrl+C to stop)...")
    last_mtimes: dict[Path, float] = {}

    def get_mtimes() -> dict[Path, float]:
        mtimes: dict[Path, float] = {}
        for rel in SRC_FILES:
            f = FRONTEND_SRC_DIR / rel
            if f.exists():
                mtimes[f] = f.stat().st_mtime
        return mtimes

    last_mtimes = get_mtimes()
    build()

    try:
        while True:
            time.sleep(1.0)
            current_mtimes = get_mtimes()
            if current_mtimes != last_mtimes:
                print(f"[{time.strftime('%H:%M:%S')}] Detected change in source files, rebuilding...")
                build()
                last_mtimes = current_mtimes
    except KeyboardInterrupt:
        print("\nWatcher stopped.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Multizone Thermostat frontend bundler")
    parser.add_argument("--check", action="store_true", help="Check if bundle is up-to-date without writing")
    parser.add_argument("--watch", action="store_true", help="Watch source files and rebuild on change")
    args = parser.parse_args()

    if args.watch:
        watch()
    elif args.check:
        if not build(check_only=True):
            sys.exit(1)
    else:
        build(check_only=False)


if __name__ == "__main__":
    main()
