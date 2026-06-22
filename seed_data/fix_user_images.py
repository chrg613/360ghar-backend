#!/usr/bin/env python3
"""
Fix seed user profile images.

Uploads real avatar images from seed_data/media/users/ to Cloudinary,
then updates every seed user's profile_image_url with the correct URL.

Usage:
    uv run python seed_data/fix_user_images.py              # Preview (dry-run)
    uv run python seed_data/fix_user_images.py --apply       # Actually fix
    uv run python seed_data/fix_user_images.py --verify-only # Just check current state
"""

from __future__ import annotations

import argparse
import asyncio
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, update

from app.core.database import AsyncSessionLocal
from app.core.logging import get_logger, setup_logging
from app.models.users import User

logger = get_logger(__name__)

SEED_DATA_DIR = Path(__file__).resolve().parent
MEDIA_USERS_DIR = SEED_DATA_DIR / "media" / "users"

_used_images: list[str] = []


def _parse_user_image_filename(filename: str) -> dict[str, str] | None:
    stem = Path(filename).stem
    parts = stem.split("_")
    if len(parts) < 4:
        return None
    return {"gender": parts[0], "age": parts[1].replace("yr", ""), "name": parts[2], "hash": parts[3], "filename": filename}


def _build_user_image_pool() -> list[dict[str, str]]:
    pool: list[dict[str, str]] = []
    if not MEDIA_USERS_DIR.exists():
        return pool
    for f in MEDIA_USERS_DIR.iterdir():
        if f.is_file() and not f.name.startswith("."):
            parsed = _parse_user_image_filename(f.name)
            if parsed:
                parsed["path"] = f"media/users/{f.name}"
                pool.append(parsed)
    return pool


USER_IMAGE_POOL = _build_user_image_pool()


def _match_user_image(gender: str, first_name: str) -> str:
    name_lower = first_name.lower()
    gender_key = "female" if gender == "F" else "male"

    for img in USER_IMAGE_POOL:
        if img["gender"] == gender_key and img["name"] == name_lower and img["path"] not in _used_images:
            _used_images.append(img["path"])
            return img["path"]

    for img in USER_IMAGE_POOL:
        if img["gender"] == gender_key and img["path"] not in _used_images:
            _used_images.append(img["path"])
            return img["path"]

    for img in USER_IMAGE_POOL:
        if img["path"] not in _used_images:
            _used_images.append(img["path"])
            return img["path"]

    return random.choice(USER_IMAGE_POOL)["path"] if USER_IMAGE_POOL else ""


def _parse_gender_and_first(full_name: str, current_url: str | None) -> tuple[str, str]:
    first_name = full_name.split(" ")[0] if full_name else ""

    if current_url:
        filename = Path(current_url).stem
        parts = filename.split("_")
        if len(parts) >= 4 and parts[0] in ("male", "female"):
            return ("F" if parts[0] == "female" else "M", parts[2])

    male_names = {"arjun", "deepak", "rahul", "rohit", "vikram", "ankit", "pranav",
                  "suresh", "rajesh", "amit", "sanjay", "pankaj", "karan", "manish"}
    female_names = {"swati", "kavita", "pooja", "anjali", "divya", "priya", "ritu",
                    "rekha", "nisha", "arti", "neha", "sneha", "ishita", "ananya", "kavya",
                    "riya", "sophia", "emily", "jennifer", "sarah", "lisa", "jessica",
                    "michelle", "amanda", "ashley", "elizabeth", "laura", "mary", "meera",
                    "linda", "barbara"}

    if first_name.lower() in male_names:
        return ("M", first_name)
    elif first_name.lower() in female_names:
        return ("F", first_name)
    else:
        return ("M", first_name)


async def upload_all_user_images_to_cloudinary(dry_run: bool = False) -> dict[str, str]:
    """Upload all user avatar images from seed_data/media/users/ to Cloudinary.

    Returns a dict mapping local ref (e.g. "media/users/male_22yr_arjun_4D325114.webp")
    to Cloudinary secure_url.
    """
    media_urls: dict[str, str] = {}

    if not MEDIA_USERS_DIR.exists():
        logger.warning("Media users directory not found: %s", MEDIA_USERS_DIR)
        return media_urls

    try:
        from app.services.cloudinary import cloudinary_service
    except Exception as exc:
        logger.warning("Cloudinary service not available (%s). Using local paths.", exc)
        if dry_run:
            for f in sorted(MEDIA_USERS_DIR.iterdir()):
                if f.is_file() and not f.name.startswith("."):
                    ref = f"media/users/{f.name}"
                    media_urls[ref] = ref
        return media_urls

    files = sorted([f for f in MEDIA_USERS_DIR.iterdir() if f.is_file() and not f.name.startswith(".")])
    logger.info("Uploading %d avatar images to Cloudinary...", len(files))

    for local_path in files:
        ref = f"media/users/{local_path.name}"
        if dry_run:
            logger.info("[DRY RUN] Would upload: %s", ref)
            media_urls[ref] = f"https://res.cloudinary.com/placeholder/{ref}"
            continue

        try:
            # Convert to WebP before uploading
            from app.services.image_processing import optimize_for_web

            file_bytes = local_path.read_bytes()
            try:
                optimized_bytes, content_type = optimize_for_web(
                    file_bytes, max_dimension=512, quality=85
                )
            except Exception:
                logger.warning("WebP conversion failed for %s, using original", ref)
                optimized_bytes = file_bytes
                content_type = _infer_content_type(local_path.name)

            # Use .webp extension in public_id if converted
            stem = local_path.stem
            if content_type == "image/webp":
                public_id = f"avatars/seed/{stem}.webp"
            else:
                public_id = f"avatars/seed/{stem}"

            def _upload(data: bytes, pid: str, ct: str) -> dict:
                return cloudinary_service.upload_file(
                    file_bytes=data,
                    public_id=pid,
                    folder="360ghar",
                    content_type=ct,
                    is_image=True,
                    overwrite=True,
                )

            result = await asyncio.get_event_loop().run_in_executor(
                None, _upload, optimized_bytes, public_id, content_type
            )
            url = result["secure_url"]
            logger.info("Uploaded: %s → %s", ref, url)
            media_urls[ref] = url
        except Exception as exc:
            logger.error("Failed to upload %s: %s", ref, exc)

    logger.info("Uploaded %d/%d images to Cloudinary", len(media_urls), len(files))
    return media_urls


async def fix_users(media_urls: dict[str, str], dry_run: bool = True) -> int:
    """Update seed user profile_image_url with Cloudinary URLs."""
    global _used_images
    _used_images = []

    if not USER_IMAGE_POOL:
        logger.error("No user images found in %s", MEDIA_USERS_DIR)
        return 0

    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.is_seed_data).order_by(User.id)
        result = await session.execute(stmt)
        users = list(result.scalars().all())

    logger.info("Found %d seed users to fix", len(users))

    fixed = 0
    for user in users:
        gender, first = _parse_gender_and_first(user.full_name or "", user.profile_image_url)
        matched_local = _match_user_image(gender, first)

        if not matched_local:
            logger.warning("No matching image for user %d (%s)", user.id, user.full_name)
            continue

        new_url = media_urls.get(matched_local, matched_local)

        if not dry_run:
            async with AsyncSessionLocal() as session:
                stmt = update(User).where(User.id == user.id).values(profile_image_url=new_url)
                await session.execute(stmt)
                await session.commit()

        action = "[DRY RUN]" if dry_run else "UPDATED"
        logger.info(
            "  %s User %d (%s): %s → %s",
            action,
            user.id,
            user.full_name,
            user.profile_image_url or "(none)",
            new_url,
        )
        fixed += 1

    logger.info("Done: %d users %s", fixed, "would be fixed" if dry_run else "fixed")
    return fixed


async def verify_users() -> list[dict]:
    """Query seed users and report their current image state."""
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.is_seed_data).order_by(User.id)
        result = await session.execute(stmt)
        users = list(result.scalars().all())

    logger.info("Found %d seed users in database", len(users))

    results = []
    if not USER_IMAGE_POOL:
        logger.warning("No images available in %s for comparison", MEDIA_USERS_DIR)

    for user in users:
        gender, first = _parse_gender_and_first(user.full_name or "", user.profile_image_url)
        matched = _match_user_image(gender, first) if USER_IMAGE_POOL else ""

        current = user.profile_image_url or "(none)"
        is_placeholder = not current.startswith("http")

        needs_fix = is_placeholder or (matched and matched not in current)

        results.append({
            "id": user.id,
            "full_name": user.full_name,
            "current_url": current,
            "matched_path": matched,
            "needs_fix": needs_fix,
        })

        logger.info(
            "  User %d: %-25s current=%-55s fix=%s",
            user.id,
            user.full_name or "?",
            current[:52],
            results[-1]["needs_fix"],
        )

    return results


async def main() -> None:
    setup_logging()

    parser = argparse.ArgumentParser(description="Fix seed user profile images")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Preview without changes (default)")
    parser.add_argument("--apply", action="store_true", help="Apply fixes (default is dry-run)")
    parser.add_argument("--verify-only", action="store_true", help="Only verify current state")
    args = parser.parse_args()

    dry_run = not args.apply

    if args.verify_only:
        logger.info("=== VERIFYING SEED USER IMAGES ===")
        results = await verify_users()
        needs_fix = sum(1 for r in results if r["needs_fix"])
        total = len(results)
        logger.info("Total: %d seed users, %d need fix", total, needs_fix)
        return

    logger.info("=== FIXING SEED USER IMAGES ===")
    if dry_run:
        logger.info("DRY RUN MODE — no changes will be made")

    logger.info("Step 1: Uploading avatar images to Cloudinary...")
    media_urls = await upload_all_user_images_to_cloudinary(dry_run=dry_run)
    logger.info("Got %d media URL mappings", len(media_urls))

    logger.info("Step 2: Updating seed user profile_image_url...")
    fixed = await fix_users(media_urls, dry_run=dry_run)

    if fixed == 0:
        logger.info("No users needed fixing")
    elif dry_run:
        logger.info("Run with --apply to apply %d fixes", fixed)
    else:
        logger.info("Successfully fixed %d seed user profile images", fixed)


if __name__ == "__main__":
    asyncio.run(main())
