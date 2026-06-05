"""
Optimize seed property images: convert PNG photos to WebP (quality=90)
while keeping floor plans as lossless PNG. Updates property.json references.

Usage:
    uv run python scripts/optimize_seed_images.py                      # full run
    uv run python scripts/optimize_seed_images.py --dry-run            # preview only
    uv run python scripts/optimize_seed_images.py --subdir 00121       # single property
"""
from __future__ import annotations

import json
import os
import sys
import time
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from PIL import Image

SEED_DIR = Path(__file__).parent.parent / "seed_data" / "hardcoded" / "properties"
WEBP_QUALITY = 90

KEEP_PNG = {"floor_plan.png"}

PNG_CONVERTED = 0
PNG_SKIPPED_FLOORPLAN = 0
PNG_SKIPPED_ALREADY_SMALL = 0
PNG_ERRORS = 0
JSON_UPDATED = 0
JSON_ERRORS = 0

TOTAL_INPUT_SIZE = 0
TOTAL_OUTPUT_SIZE = 0


def convert_png_to_webp(filepath: Path, dry_run: bool = False) -> tuple[int, int] | None:
    """Convert a PNG to WebP at quality=90, stripping metadata.

    Returns (original_size, new_size) or None if unchanged/skipped.
    """
    global TOTAL_INPUT_SIZE
    original_size = filepath.stat().st_size
    TOTAL_INPUT_SIZE += original_size

    try:
        with Image.open(filepath) as img:
            mode_normalized = False
            working_img = img
            if img.mode in ("RGBA", "LA") or (
                img.mode == "P" and "transparency" in img.info
            ):
                working_img = img.convert("RGBA")
                mode_normalized = True
            elif img.mode == "P":
                working_img = img.convert("RGB")
                mode_normalized = True

            try:
                output = BytesIO()
                working_img.save(
                    output,
                    format="WEBP",
                    quality=WEBP_QUALITY,
                    optimize=True,
                )
                webp_bytes = output.getvalue()
            finally:
                if mode_normalized:
                    working_img.close()

        if len(webp_bytes) >= original_size:
            return None

        new_path = filepath.with_suffix(".webp")
        new_size = len(webp_bytes)
        global TOTAL_OUTPUT_SIZE
        TOTAL_OUTPUT_SIZE += new_size

        if not dry_run:
            new_path.write_bytes(webp_bytes)
            filepath.unlink()

        return original_size, new_size

    except Exception as e:
        global PNG_ERRORS
        PNG_ERRORS += 1
        print(f"  ERROR converting {filepath.name}: {e}")
        TOTAL_OUTPUT_SIZE += original_size
        return None


def walk_and_convert(root_dir: Path, dry_run: bool = False):
    """Walk the directory tree and convert PNGs to WebP."""
    global PNG_CONVERTED, PNG_SKIPPED_FLOORPLAN, PNG_SKIPPED_ALREADY_SMALL

    for filepath in sorted(root_dir.rglob("*.png")):
        filename = filepath.name.lower()

        if filename in KEEP_PNG:
            PNG_SKIPPED_FLOORPLAN += 1
            continue

        if filepath.stat().st_size < 50_000:
            PNG_SKIPPED_ALREADY_SMALL += 1
            continue

        rel = filepath.relative_to(SEED_DIR)
        result = convert_png_to_webp(filepath, dry_run=dry_run)

        if result is None:
            print(f"  SKIP  {rel}  (already efficient or error)")
        else:
            orig, new = result
            saved_pct = (1 - new / orig) * 100
            PNG_CONVERTED += 1
            print(
                f"  OK    {rel}  "
                f"{orig / 1024:.0f}KB → {new / 1024:.0f}KB  "
                f"({saved_pct:.0f}% saved)"
            )


def update_property_json_refs(json_path: Path, dry_run: bool = False) -> bool:
    """Update .png → .webp in property.json, except for floor_plan.png."""
    global JSON_UPDATED

    with open(json_path, "r") as f:
        data = json.load(f)

    def _walk_and_replace(obj) -> bool:
        modified = False
        if isinstance(obj, dict):
            for key, val in list(obj.items()):
                if isinstance(val, str) and val.endswith(".png"):
                    basename = os.path.basename(val)
                    if basename not in KEEP_PNG:
                        obj[key] = val[:-4] + ".webp"
                        modified = True
                elif isinstance(val, (dict, list)):
                    if _walk_and_replace(val):
                        modified = True
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                if isinstance(item, str) and item.endswith(".png"):
                    basename = os.path.basename(item)
                    if basename not in KEEP_PNG:
                        obj[i] = item[:-4] + ".webp"
                        modified = True
                elif isinstance(item, (dict, list)):
                    if _walk_and_replace(item):
                        modified = True
        return modified

    modified = _walk_and_replace(data)

    if modified:
        JSON_UPDATED += 1
        if not dry_run:
            with open(json_path, "w") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    return modified


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Optimize seed property images to WebP"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying files",
    )
    parser.add_argument(
        "--subdir",
        type=str,
        default=None,
        help="Only process a specific property subdirectory (e.g. 00121)",
    )
    args = parser.parse_args()

    root = SEED_DIR
    if args.subdir:
        root = root / args.subdir
        if not root.exists():
            print(f"ERROR: {root} does not exist")
            sys.exit(1)

    if args.dry_run:
        print(f"🔍 DRY RUN — no files will be modified\n")

    print(f"Scanning {root} for PNG images...\n")

    start = time.time()

    # Pass 1: convert images
    walk_and_convert(root, dry_run=args.dry_run)

    # Pass 2: update property.json references
    for json_path in sorted(root.rglob("property.json")):
        if json_path.stat().st_size == 0:
            continue
        rel = json_path.relative_to(SEED_DIR)
        if update_property_json_refs(json_path, dry_run=args.dry_run):
            print(f"  JSON  {rel}  (updated .png → .webp references)")

    elapsed = time.time() - start

    print(f"\n{'─' * 60}")
    print(f"Results ({'DRY RUN' if args.dry_run else 'COMPLETED'}):")
    print(f"  Images converted to WebP:   {PNG_CONVERTED}")
    print(f"  Floor plans kept as PNG:    {PNG_SKIPPED_FLOORPLAN}")
    print(f"  Already small/skipped:      {PNG_SKIPPED_ALREADY_SMALL}")
    print(f"  Conversion errors:          {PNG_ERRORS}")
    print(f"  property.json files updated: {JSON_UPDATED}")
    if TOTAL_OUTPUT_SIZE > 0 and TOTAL_INPUT_SIZE > 0:
        saved_gb = (TOTAL_INPUT_SIZE - TOTAL_OUTPUT_SIZE) / (1024**3)
        pct = (1 - TOTAL_OUTPUT_SIZE / TOTAL_INPUT_SIZE) * 100
        print(f"  Space saved:                {saved_gb:.2f} GB ({pct:.0f}%)")
    print(f"  Time taken:                 {elapsed:.1f}s")


if __name__ == "__main__":
    main()
